# 小猪素材管理工具 | streamlit构建
# 单文件
# 在本地开放8080端口运行，访问http://localhost:8080
# 运行: streamlit run pig_manager.py --server.port 8080

import streamlit as st
from PIL import Image
import io
import json
from pathlib import Path

# Hardcoded paths
PIG_JSON_PATH = Path("./resource/pig.json")
IMAGE_DIR = Path("./resource/image")


def load_pigs():
    """Load pig data from JSON file."""
    if not PIG_JSON_PATH.exists():
        return []
    return json.loads(PIG_JSON_PATH.read_text("utf-8"))


def save_pigs(pigs):
    """Save pig data to JSON file."""
    PIG_JSON_PATH.write_text(
        json.dumps(pigs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_image_path(pig_id):
    """Get image path for a pig ID, trying multiple extensions."""
    for ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        path = IMAGE_DIR / f"{pig_id}.{ext}"
        if path.exists():
            return path
    return None


def get_existing_image_extensions(pig_id):
    """Get list of existing image extensions for a pig ID."""
    extensions = []
    for ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        path = IMAGE_DIR / f"{pig_id}.{ext}"
        if path.exists():
            extensions.append(ext)
    return extensions


def delete_pig_image(pig_id):
    """Delete all image files for a pig ID."""
    for ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        path = IMAGE_DIR / f"{pig_id}.{ext}"
        if path.exists():
            path.unlink()


def save_uploaded_image(uploaded_file, pig_id):
    """Save uploaded image file with pig ID."""
    file_ext = uploaded_file.name.split(".")[-1].lower()
    if file_ext not in ["png", "jpg", "jpeg", "webp", "gif"]:
        return False

    # Delete existing images with the same ID
    delete_pig_image(pig_id)

    # Save new image
    output_path = IMAGE_DIR / f"{pig_id}.{file_ext}"
    output_path.write_bytes(uploaded_file.getbuffer())
    return True


def save_cropped_image(image_bytes, file_ext, pig_id):
    """Save cropped image with pig ID."""
    if file_ext not in ["png", "jpg", "jpeg", "webp", "gif"]:
        return False

    # Delete existing images with the same ID
    delete_pig_image(pig_id)

    # Save new cropped image
    output_path = IMAGE_DIR / f"{pig_id}.{file_ext}"
    output_path.write_bytes(image_bytes)
    return True


def main():
    st.set_page_config(page_title="小猪素材管理工具", layout="wide")
    st.title("🐷 小猪素材管理工具")

    # Load data
    pigs = load_pigs()

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📋 小猪列表", "➕ 添加小猪", "✏️ 编辑小猪"])

    # Tab 1: List view
    with tab1:
        st.subheader("所有小猪")

        if not pigs:
            st.info("暂无小猪数据")
        else:
            # Display data in columns
            cols = st.columns(3)
            for idx, pig in enumerate(pigs):
                col_idx = idx % 3
                with cols[col_idx]:
                    # Card container
                    with st.container():
                        # Image
                        img_path = get_image_path(pig["id"])
                        if img_path:
                            st.image(str(img_path), width=150)
                        else:
                            st.info("暂无图片")

                        # Info
                        st.markdown(f"**ID:** `{pig['id']}`")
                        st.markdown(f"**名称:** {pig['name']}")
                        st.markdown(f"**描述:** {pig['description']}")

                        # Expandable analysis
                        with st.expander("查看详细解析"):
                            st.text(pig["analysis"])

                        # Delete button
                        if st.button(
                            "🗑️ 删除",
                            key=f"delete_{pig['id']}",
                            use_container_width=True,
                        ):
                            st.session_state[f"delete_confirm_{pig['id']}"] = True

                    st.divider()

            # Handle delete confirmations
            for pig in pigs:
                if st.session_state.get(f"delete_confirm_{pig['id']}", False):
                    st.warning(f"确认删除小猪「{pig['name']}」？")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "✅ 确认删除", key=f"confirm_{pig['id']}", type="primary"
                        ):
                            # Delete image files
                            delete_pig_image(pig["id"])
                            # Remove from JSON
                            pigs = [p for p in pigs if p["id"] != pig["id"]]
                            save_pigs(pigs)
                            st.success(f"已删除小猪「{pig['name']}」")
                            st.session_state[f"delete_confirm_{pig['id']}"] = False
                            st.rerun()
                    with col2:
                        if st.button("❌ 取消", key=f"cancel_{pig['id']}"):
                            st.session_state[f"delete_confirm_{pig['id']}"] = False
                            st.rerun()

    # Tab 2: Add new pig
    with tab2:
        st.subheader("添加新小猪")

        # JSON parse section
        st.markdown("---")
        st.markdown("**📥 JSON 快捷导入**")
        st.caption("输入JSON数据，点击解析按钮自动填充到下方表单")

        col1, col2 = st.columns([3, 1])
        with col1:
            json_input = st.text_area(
                "JSON数据",
                placeholder='{"id": "pig_001", "name": "小猪名字", "description": "描述", "analysis": "详细解析"}',
                help="支持原json格式，将自动解析并填充到表单",
                key="json_parse_input",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔍 解析JSON", use_container_width=True):
                try:
                    if json_input.strip():
                        parsed = json.loads(json_input)
                        if all(
                            k in parsed
                            for k in ["id", "name", "description", "analysis"]
                        ):
                            st.session_state["form_pig_id"] = parsed["id"]
                            st.session_state["form_pig_name"] = parsed["name"]
                            st.session_state["form_pig_description"] = parsed[
                                "description"
                            ]
                            st.session_state["form_pig_analysis"] = parsed["analysis"]
                            st.success("JSON解析成功！已填充到表单")
                            st.rerun()
                        else:
                            st.error(
                                "JSON缺少必要字段：id, name, description, analysis"
                            )
                    else:
                        st.warning("请输入JSON数据")
                except json.JSONDecodeError as e:
                    st.error(f"JSON格式错误: {e}")

        st.markdown("---")

        # Image upload and cropping section (outside form)
        st.markdown("**🖼️ 图片上传与裁剪**")

        # Initialize cropping state
        if "cropped_image" not in st.session_state:
            st.session_state.cropped_image = None
        if "cropped_format" not in st.session_state:
            st.session_state.cropped_format = None

        # File upload (outside form)
        uploaded_file = st.file_uploader(
            "选择图片", type=["png", "jpg", "jpeg", "webp", "gif"], key="image_uploader"
        )

        if uploaded_file:
            # Show original preview
            st.markdown("**原图预览:**")
            st.image(uploaded_file, width=300)

            # Show cropping component
            st.markdown("**拖动选择裁剪区域:**")
            from streamlit_cropper import st_cropper

            img = Image.open(uploaded_file)
            cropped_img = st_cropper(
                img,
                realtime_update=True,
                box_color="#FF4B4B",
                aspect_ratio=(1, 1),
                return_type="image",
            )

            # Confirm crop button
            if st.button("✅ 确认裁剪", key="confirm_crop"):
                img_byte_arr = io.BytesIO()
                file_ext = uploaded_file.name.split(".")[-1].lower()
                format_map = {
                    "jpg": "JPEG",
                    "jpeg": "JPEG",
                    "png": "PNG",
                    "webp": "WEBP",
                    "gif": "GIF",
                }
                img_format = format_map.get(file_ext, "PNG")
                cropped_img.save(img_byte_arr, format=img_format)
                st.session_state.cropped_image = img_byte_arr.getvalue()
                st.session_state.cropped_format = file_ext
                st.success("裁剪完成！")
                st.rerun()

        # Show cropped preview
        if st.session_state.cropped_image:
            st.markdown("**裁剪后的图片:**")
            st.image(st.session_state.cropped_image, width=200)
            if st.button("🗑️ 清除裁剪", key="clear_crop"):
                st.session_state.cropped_image = None
                st.session_state.cropped_format = None
                st.rerun()

        st.markdown("---")

        with st.form("add_pig_form"):
            pig_id = st.text_input(
                "ID", key="form_pig_id", help="小猪的唯一标识符，将作为图片文件名"
            )

            pig_name = st.text_input("名称", key="form_pig_name")

            pig_description = st.text_area(
                "描述",
                key="form_pig_description",
                max_chars=200,
                help="简短描述，建议200字以内",
            )

            pig_analysis = st.text_area(
                "详细解析", key="form_pig_analysis", help="小猪的性格分析和详细介绍"
            )

            submitted = st.form_submit_button("➕ 添加小猪", type="primary")

            if submitted:
                # Validate required fields
                if (
                    not pig_id
                    or not pig_name
                    or not pig_description
                    or not pig_analysis
                ):
                    st.error("请填写所有必填字段（ID、名称、描述、详细解析）")
                elif not st.session_state.cropped_image:
                    st.error("请先上传并裁剪图片")
                else:
                    # Check if ID already exists
                    existing_ids = [p["id"] for p in pigs]
                    if pig_id in existing_ids:
                        st.error(f"ID '{pig_id}' 已存在，请使用其他ID")
                    else:
                        # Save cropped image
                        if save_cropped_image(
                            st.session_state.cropped_image,
                            st.session_state.cropped_format,
                            pig_id,
                        ):
                            # Create new pig entry
                            new_pig = {
                                "id": pig_id,
                                "name": pig_name,
                                "description": pig_description,
                                "analysis": pig_analysis,
                            }
                            pigs.append(new_pig)
                            save_pigs(pigs)
                            st.success(f"成功添加小猪「{pig_name}」！")
                            # Clear cropped image state
                            st.session_state.cropped_image = None
                            st.session_state.cropped_format = None
                            st.rerun()
                        else:
                            st.error("图片保存失败，请检查图片格式")

    # Tab 3: Edit pig
    with tab3:
        st.subheader("编辑小猪")

        # Select pig to edit
        if not pigs:
            st.info("暂无小猪数据")
        else:
            pig_options = {f"{p['name']} ({p['id']})": p for p in pigs}
            selected = st.selectbox(
                "选择要编辑的小猪", options=list(pig_options.keys())
            )

            if selected:
                pig = pig_options[selected]

                # Initialize edit cropping state
                if "edit_cropped_image" not in st.session_state:
                    st.session_state.edit_cropped_image = None
                if "edit_cropped_format" not in st.session_state:
                    st.session_state.edit_cropped_format = None

                # Show current image
                current_img_path = get_image_path(pig["id"])
                if current_img_path:
                    st.markdown("**当前图片:**")
                    st.image(str(current_img_path), width=200)

                # Image replacement section (outside form)
                st.markdown("---")
                st.markdown("**🖼️ 图片替换（可选）**")

                replace_image = st.checkbox(
                    "替换图片", key="replace_image_checkbox", value=False
                )

                if replace_image:
                    # Clear edit cropped state when checkbox is first checked
                    if (
                        st.session_state.get("replace_image_checkbox")
                        and not st.session_state.edit_cropped_image
                    ):
                        st.session_state.edit_cropped_image = None
                        st.session_state.edit_cropped_format = None

                    # File upload (outside form)
                    edit_uploaded_file = st.file_uploader(
                        "选择新图片",
                        type=["png", "jpg", "jpeg", "webp", "gif"],
                        key="edit_image_uploader",
                    )

                    if edit_uploaded_file:
                        # Show original preview
                        st.markdown("**新图片预览:**")
                        st.image(edit_uploaded_file, width=300)

                        # Show cropping component
                        st.markdown("**拖动选择裁剪区域:**")
                        from streamlit_cropper import st_cropper

                        img = Image.open(edit_uploaded_file)
                        cropped_img = st_cropper(
                            img,
                            realtime_update=True,
                            box_color="#FF4B4B",
                            aspect_ratio=(1, 1),
                            return_type="image",
                        )

                        # Confirm crop button
                        if st.button("✅ 确认裁剪", key="edit_confirm_crop"):
                            img_byte_arr = io.BytesIO()
                            file_ext = edit_uploaded_file.name.split(".")[-1].lower()
                            format_map = {
                                "jpg": "JPEG",
                                "jpeg": "JPEG",
                                "png": "PNG",
                                "webp": "WEBP",
                                "gif": "GIF",
                            }
                            img_format = format_map.get(file_ext, "PNG")
                            cropped_img.save(img_byte_arr, format=img_format)
                            st.session_state.edit_cropped_image = (
                                img_byte_arr.getvalue()
                            )
                            st.session_state.edit_cropped_format = file_ext
                            st.success("裁剪完成！")
                            st.rerun()

                    # Show cropped preview
                    if st.session_state.edit_cropped_image:
                        st.markdown("**裁剪后的图片:**")
                        st.image(st.session_state.edit_cropped_image, width=200)
                        if st.button("🗑️ 清除裁剪", key="edit_clear_crop"):
                            st.session_state.edit_cropped_image = None
                            st.session_state.edit_cropped_format = None
                            st.rerun()

                    st.markdown("---")

                with st.form("edit_pig_form"):
                    # Pre-fill form with current data
                    st.text_input(
                        "ID", value=pig["id"], disabled=True, help="ID不可修改"
                    )

                    edit_name = st.text_input("名称", value=pig["name"])

                    edit_description = st.text_area(
                        "描述", value=pig["description"], max_chars=200
                    )

                    edit_analysis = st.text_area("详细解析", value=pig["analysis"])

                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("💾 保存修改", type="primary")

                    with col2:
                        if st.form_submit_button("❌ 取消"):
                            st.rerun()

                    if submitted:
                        # Validate required fields
                        if not edit_name or not edit_description or not edit_analysis:
                            st.error("请填写所有必填字段（名称、描述、详细解析）")
                        else:
                            # Update pig data
                            pig_index = [
                                i for i, p in enumerate(pigs) if p["id"] == pig["id"]
                            ][0]
                            pigs[pig_index]["name"] = edit_name
                            pigs[pig_index]["description"] = edit_description
                            pigs[pig_index]["analysis"] = edit_analysis

                            # Handle image replacement
                            if replace_image and st.session_state.edit_cropped_image:
                                if save_cropped_image(
                                    st.session_state.edit_cropped_image,
                                    st.session_state.edit_cropped_format,
                                    pig["id"],
                                ):
                                    st.success("图片已更新")
                                else:
                                    st.error("图片更新失败")

                            save_pigs(pigs)
                            st.success(f"成功更新小猪「{edit_name}」！")
                            # Clear edit cropped image state
                            st.session_state.edit_cropped_image = None
                            st.session_state.edit_cropped_format = None
                            st.rerun()


if __name__ == "__main__":
    main()
