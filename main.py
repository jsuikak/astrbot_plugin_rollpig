import asyncio
import datetime
from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools, register
from astrbot.core import AstrBotConfig
from astrbot.core.message.components import At

from .rollpig.dedup import get_history_days, pick_pig_for_user
from .rollpig.render import PigImageRenderer
from .rollpig.storage import load_history_file, load_json, save_json


class RollPigPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # 配置项
        self.admins_id: list[str] = context.get_config().get("admins_id", [])
        self.at_view_pig: bool = self.config.get("at_view_pig", False)

        raw_history_days = self.config.get("history_days", 5)
        self.history_days = get_history_days(raw_history_days)
        try:
            if int(raw_history_days) < 1:
                raise ValueError
        except (TypeError, ValueError):
            logger.warning(
                f"history_days 配置无效（{raw_history_days}），将回退为默认值 5"
            )

        # 初始化路径
        self.plugin_dir = Path(__file__).parent
        self.plugin_data_dir = StarTools.get_data_dir("astrbot_plugin_rollpig")
        self.res_dir = self.plugin_dir / "resource"
        self.font_dir = self.res_dir / "font"
        self.piginfo_path = self.res_dir / "pig.json"
        self.image_dir = self.res_dir / "image"

        self.plugin_data_dir.mkdir(parents=True, exist_ok=True)
        self.font_dir.mkdir(parents=True, exist_ok=True)

        self.pig_list = load_json(self.piginfo_path, [], logger_obj=logger)
        if not self.pig_list:
            logger.error("小猪信息为空或不存在，请检查资源文件！")

        self.today_path = self.plugin_data_dir / "rollpig_today.json"
        self.history_path = self.plugin_data_dir / "rollpig_history.json"

        # 渲染逻辑交由独立模块
        self.renderer = PigImageRenderer(
            image_dir=self.image_dir,
            font_dir=self.font_dir,
            logger=logger,
        )

    def get_at_ids(self, event: AstrMessageEvent) -> list[str]:
        """
        获取QQ被at用户的id列表
        :param event: Aiocqhttp消息事件对象
        :return: 被at用户的id列表（排除自己）
        """
        return [
            str(seg.qq)
            for seg in event.get_messages()
            if (isinstance(seg, At) and str(seg.qq) != event.get_self_id())
        ]

    def is_at_bot(self, event: AstrMessageEvent) -> bool:
        """检查消息中是否@了机器人自己"""
        for seg in event.get_messages():
            if isinstance(seg, At) and str(seg.qq) == event.get_self_id():
                return True
        return False

    @filter.command("今日小猪", alias={"抽小猪", "我的小猪", "rollpig"})
    async def roll_pig(self, event: AstrMessageEvent):
        """抽取今日小猪"""
        today = datetime.date.today()
        today_str = today.isoformat()
        user_id = event.get_sender_id()

        if self.at_view_pig:
            parts = event.message_str.strip().split()
            at_ids = self.get_at_ids(event)
            if len(at_ids) > 1:
                await event.send(event.plain_result("一次只能抽取一个小猪哦！"))
                return
            if self.is_at_bot(event):
                user_id = event.get_self_id()
            elif len(parts) >= 2:
                if at_ids[0] not in self.admins_id:
                    user_id = at_ids[0]
                else:
                    await event.send(event.plain_result("你这只小猪，不许对主人不敬！"))
                    return

        today_cache = load_json(
            self.today_path, {"date": "", "records": {}}, logger_obj=logger
        )
        if today_cache.get("date") != today_str:
            today_cache = {"date": today_str, "records": {}}
        user_records = today_cache["records"]

        # 今日已抽取
        if user_id in user_records:
            pig = user_records[user_id]
            await self.send_rendered_pig(event, pig, user_id)
            return

        if not self.pig_list:
            await event.send(event.plain_result("小猪信息加载失败，请检查后台报错！"))
            # 返回
            return

        # 加载历史记录
        history_data = load_history_file(self.history_path, logger_obj=logger)
        pig, history_data = pick_pig_for_user(
            pig_list=self.pig_list,
            history_data=history_data,
            user_id=user_id,
            today=today,
            history_days=self.history_days,
        )

        user_records[user_id] = pig
        save_json(self.today_path, today_cache)
        save_json(self.history_path, history_data)

        await self.send_rendered_pig(event, pig, user_id)

    async def send_rendered_pig(
        self, event: AstrMessageEvent, pig_data: dict, user_id: str
    ):
        """合成并发送小猪图片"""
        img_path = await asyncio.to_thread(self.renderer.render_pig_image, pig_data)
        if img_path and img_path.exists():
            try:
                chain = [Comp.Plain(". 这是你的今日小猪：")]
                group_id = event.get_group_id()
                if group_id:
                    chain.insert(0, Comp.At(qq=user_id))
                await event.send(event.chain_result(chain))
                await event.send(event.image_result(str(img_path.absolute())))
                logger.info("合成图片发送成功")
                return
            except Exception as e:
                logger.error(f"发送合成图片失败：{str(e)}")
            finally:
                try:
                    img_path.unlink(missing_ok=True)
                except Exception as cleanup_err:
                    logger.warning(f"清理临时图片失败：{cleanup_err}")

        await self.send_fallback_msg(event, pig_data)

    async def send_fallback_msg(self, event: AstrMessageEvent, pig_data: dict):
        """降级发送：原始图片 + 纯文本"""
        pig_name = pig_data.get("name", "未知小猪")
        pig_desc = pig_data.get("description", "无描述")
        pig_analysis = pig_data.get("analysis", "无解析")
        pig_id = pig_data.get("id", "")

        text_msg = (
            f"【今日小猪】\n名称：{pig_name}\n描述：{pig_desc}\n解析：{pig_analysis}"
        )
        msg_chain = []

        avatar_path = self.renderer.find_image_file(pig_id)
        if avatar_path and avatar_path.exists():
            try:
                msg_chain.append(Comp.Image.fromFileSystem(str(avatar_path.absolute())))
            except Exception as e:
                logger.error(f"发送原始图片失败：{str(e)}")
                text_msg += "\n\n（图片发送失败，仅展示文字信息）"

        msg_chain.append(Comp.Plain(text_msg))
        await event.send(event.chain_result(msg_chain))

    async def terminate(self):
        """插件卸载清理"""
        logger.info("今日小猪插件已卸载")
