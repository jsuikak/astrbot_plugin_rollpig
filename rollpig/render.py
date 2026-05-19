import tempfile
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont


class PigImageRenderer:
    CANVAS_WIDTH = 800
    CANVAS_HEIGHT = 800
    AVATAR_SIZE = 280
    SPACING_AVATAR_NAME = 20
    SPACING_NAME_DESC = 25
    SPACING_DESC_ANALYSIS = 30
    DESC_FONT_SIZE = 32
    ANALYSIS_FONT_SIZE = 28
    ANALYSIS_LINE_HEIGHT_FACTOR = 1.6
    ANALYSIS_WIDTH_RATIO = 0.85
    NAME_FONT_SIZE = 66

    def __init__(self, image_dir: Path, font_dir: Path, logger: Any = None):
        self.image_dir = image_dir
        self.font_dir = font_dir
        self.logger = logger
        self.font_regular = self._init_regular_font()
        self.font_bold = self._init_bold_font()

    def _log(self, level: str, message: str):
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message)

    def _load_font(
        self, font_candidates: list[str | Path], size: int, purpose: str
    ) -> ImageFont.FreeTypeFont | None:
        for font_path in font_candidates:
            if Path(font_path).exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception as e:
                    self._log("warning", f"加载{purpose}字体{font_path}失败：{e}")
                    continue
        self._log("warning", f"未找到{purpose}字体，使用默认字体")
        return ImageFont.load_default()

    def _init_regular_font(self) -> ImageFont.FreeTypeFont | None:
        font_paths = [
            self.font_dir / "可爱字体.ttf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "常规")

    def _init_bold_font(self) -> ImageFont.FreeTypeFont | None:
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Bold.otf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        return self._load_font(font_paths, self.NAME_FONT_SIZE, "加粗")

    def _get_text_size(
        self, text: str, font: ImageFont.FreeTypeFont
    ) -> tuple[int, int]:
        draw = ImageDraw.Draw(PILImage.new("RGB", (1, 1)))
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])
        except Exception:
            return draw.textsize(text, font=font)

    def _draw_bold_text(
        self,
        draw: ImageDraw.ImageDraw,
        pos: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: tuple,
    ):
        x, y = pos
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for ox, oy in offsets:
            draw.text((x + ox, y + oy), text, fill=fill, font=font)
        draw.text((x, y), text, fill=fill, font=font)

    def find_image_file(self, pig_id: str) -> Path | None:
        exts = ["png", "jpg", "jpeg", "webp", "gif"]
        for ext in exts:
            file = self.image_dir / f"{pig_id}.{ext}"
            if file.exists():
                self._log("debug", f"找到的小猪图片文件：{file.absolute()}")
                return file
        self._log("warning", f"未找到小猪ID {pig_id} 对应的图片文件")
        return None

    def render_pig_image(self, pig_data: dict) -> Path | None:
        pig_id = pig_data.get("id", "")
        pig_name = pig_data.get("name", "未知小猪")
        pig_desc = pig_data.get("description", "无描述")
        pig_analysis = pig_data.get("analysis", "无解析")

        canvas_width = self.CANVAS_WIDTH
        canvas_height = self.CANVAS_HEIGHT
        canvas = PILImage.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        avatar_w, avatar_h = self.AVATAR_SIZE, self.AVATAR_SIZE
        avatar = None
        avatar_path = self.find_image_file(pig_id)
        if avatar_path:
            try:
                avatar = PILImage.open(avatar_path)
                avatar.thumbnail((avatar_w, avatar_h))
                if avatar.size != (avatar_w, avatar_h):
                    center_x = avatar.width // 2
                    center_y = avatar.height // 2
                    half = self.AVATAR_SIZE // 2
                    crop_box = (
                        center_x - half,
                        center_y - half,
                        center_x + half,
                        center_y + half,
                    )
                    avatar = avatar.crop(crop_box)
            except Exception as e:
                self._log("error", f"加载小猪图片失败：{str(e)}")
                avatar = None

        name_font = self.font_bold
        name_w, name_h = self._get_text_size(pig_name, name_font)

        desc_font = self.font_regular.font_variant(size=self.DESC_FONT_SIZE)
        desc_w, desc_h = self._get_text_size(pig_desc, desc_font)

        analysis_font = self.font_regular.font_variant(size=self.ANALYSIS_FONT_SIZE)
        line_height = int(self.ANALYSIS_FONT_SIZE * self.ANALYSIS_LINE_HEIGHT_FACTOR)
        max_analysis_width = int(canvas_width * self.ANALYSIS_WIDTH_RATIO)

        analysis_lines = []
        current_line = ""
        for char in pig_analysis:
            current_line += char
            line_w, _ = self._get_text_size(current_line, analysis_font)
            if line_w > max_analysis_width:
                analysis_lines.append(current_line[:-1])
                current_line = char
        if current_line:
            analysis_lines.append(current_line)
        analysis_total_h = len(analysis_lines) * line_height

        spacing_avatar_name = self.SPACING_AVATAR_NAME
        spacing_name_desc = self.SPACING_NAME_DESC
        spacing_desc_analysis = self.SPACING_DESC_ANALYSIS
        total_content_h = (
            avatar_h
            + spacing_avatar_name
            + name_h
            + spacing_name_desc
            + desc_h
            + spacing_desc_analysis
            + analysis_total_h
        )

        start_y = (canvas_height - total_content_h) // 2

        avatar_x = (canvas_width - avatar_w) // 2
        avatar_y = start_y
        if avatar:
            canvas.paste(
                avatar,
                (avatar_x, avatar_y),
                mask=avatar if avatar.mode == "RGBA" else None,
            )
        else:
            error_font = self.font_regular.font_variant(size=24)
            error_text = "图片加载失败"
            error_w, _ = self._get_text_size(error_text, error_font)
            error_x = (canvas_width - error_w) // 2
            draw.text((error_x, avatar_y + 120), error_text, fill=(255, 0, 0), font=error_font)

        name_y = avatar_y + avatar_h + spacing_avatar_name
        name_x = (canvas_width - name_w) // 2
        self._draw_bold_text(draw, (name_x, name_y), pig_name, name_font, (0, 0, 0))

        desc_y = name_y + name_h + spacing_name_desc
        desc_x = (canvas_width - desc_w) // 2
        draw.text((desc_x, desc_y), pig_desc, fill=(85, 85, 85), font=desc_font)

        analysis_y = desc_y + desc_h + spacing_desc_analysis
        for line in analysis_lines:
            line_w, _ = self._get_text_size(line, analysis_font)
            line_x = (canvas_width - line_w) // 2
            draw.text((line_x, analysis_y), line, fill=(51, 51, 51), font=analysis_font)
            analysis_y += line_height

        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                canvas.save(tmp_path, format="PNG", quality=95)
            self._log("debug", f"合成图片成功，临时文件路径：{tmp_path.absolute()}")
            if not tmp_path.exists():
                self._log("error", f"临时文件创建失败：{tmp_path}")
                return None
            return tmp_path
        except Exception as e:
            self._log("error", f"合成图片失败：{str(e)}")
            return None

