#!/usr/bin/env python3
"""
PPT 排版图片生成器
支持通过 layouts.json 配置文件定义布局
"""

import os
import sys
import json
import argparse
from PIL import Image

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'layouts.json')


def load_config():
    """加载布局配置文件"""
    if os.path.exists(DEFAULT_CONFIG_PATH):
        with open(DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def parse_color(color_str):
    """解析颜色字符串"""
    color_map = {
        'white': '#FFFFFF',
        'black': '#000000',
        'red': '#FF0000',
        'green': '#00FF00',
        'blue': '#0000FF',
        'yellow': '#FFFF00',
        'gray': '#808080',
        'grey': '#808080',
    }

    color_str = color_str.lower().strip()

    if color_str in color_map:
        color_str = color_map[color_str]

    if color_str.startswith('#'):
        hex_color = color_str[1:]
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    else:
        return (255, 255, 255)


def calculate_thumb_size(num_images, canvas_height, gap):
    """计算缩略图尺寸（保持16:9比例）"""
    thumb_height = (canvas_height - (num_images - 1) * gap) // num_images
    thumb_width = int(thumb_height * 16 / 9)
    return thumb_width, thumb_height


def paste_image(canvas, img, x, y, width, height):
    """将图片缩放后粘贴到画布"""
    target_ratio = 16 / 9
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        new_height = height
        new_width = int(height * img_ratio)
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - width) // 2
        resized = resized.crop((left, 0, left + width, height))
    else:
        new_width = width
        new_height = int(width / img_ratio)
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        top = (new_height - height) // 2
        resized = resized.crop((0, top, width, top + height))

    canvas.paste(resized, (x, y))


def render_three_tier(input_dir, output_path, config, layout_name):
    """三层瀑布流布局：第一层1张大图 + 第二层2张 + 第三层2张（保持16:9比例）"""
    canvas_config = config.get('canvas', {})
    defaults = config.get('defaults', {})
    layout_config = config.get('layouts', {}).get(layout_name)

    canvas_width = canvas_config.get('width', 1242)
    canvas_height = canvas_config.get('height', 1660)
    margin = layout_config.get('margin', 0)
    gap = layout_config.get('gap', 0)
    layer_gap = layout_config.get('layer_gap', 80)
    bg = parse_color(defaults.get('background', '#f3dfc6'))

    rows_config = layout_config.get('rows', [])
    row_counts = [r.get('count', 1) for r in rows_config]

    # 创建画布
    canvas = Image.new('RGB', (canvas_width, canvas_height), bg)

    # 获取所有图片
    images = sorted([f for f in os.listdir(input_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    total_needed = sum(row_counts)
    if len(images) < total_needed:
        print(f"错误：需要至少 {total_needed} 张图片，当前只有 {len(images)} 张")
        return False

    # 计算每行高度（保持16:9比例）
    content_width = canvas_width
    layer_gap = layout_config.get('layer_gap', 80)

    # 第一层：单图撑满宽度，16:9高度
    top_height = int(content_width * 9 / 16)

    # 第二三层：双图横排，每张16:9
    double_img_width = (content_width - gap) // 2
    double_img_height = int(double_img_width * 9 / 16)

    # 计算剩余空间给第二三层
    total_layer_gap = layer_gap * 2  # 两层层间距
    remaining = canvas_height - margin * 2 - top_height - total_layer_gap

    # 二三层各占一半高度（取图片高度和可用高度中较大的）
    middle_height = remaining // 2
    bottom_height = remaining - middle_height

    # 实际行高等于图片高度
    row_heights = [top_height, double_img_height, double_img_height]

    # 渲染每一行
    img_index = 0
    top_margin = 20
    y = top_margin

    for row_idx, (count, row_height) in enumerate(zip(row_counts, row_heights)):
        if count == 1:
            # 单图：宽度撑满，高度保持16:9
            img_width = content_width
            img_height = top_height
            img_path = os.path.join(input_dir, images[img_index])
            try:
                img = Image.open(img_path).convert('RGB')
                paste_image(canvas, img, 0, y, img_width, img_height)
            except Exception as e:
                print(f"警告：无法读取图片 {images[img_index]}: {e}")
            img_index += 1
        else:
            # 多图：横排，每张保持16:9
            img_width = double_img_width
            img_height = double_img_height

            for col in range(count):
                img_path = os.path.join(input_dir, images[img_index])
                try:
                    img = Image.open(img_path).convert('RGB')
                    x = col * img_width
                    paste_image(canvas, img, x, y, img_width, img_height)
                except Exception as e:
                    print(f"警告：无法读取图片 {images[img_index]}: {e}")
                img_index += 1

        y += row_height + layer_gap if row_idx < len(row_counts) - 1 else row_height

    canvas.save(output_path, 'PNG')
    print(f"已生成：{output_path}")
    return True


def render_layout(input_dir, output_path, config, layout_name, bg_color=None, custom_left=None, custom_right=None):
    """通用的布局渲染函数"""
    canvas_config = config.get('canvas', {})
    defaults = config.get('defaults', {})
    layout_config = config.get('layouts', {}).get(layout_name)

    if not layout_config:
        print(f"错误：未找到布局 '{layout_name}'")
        return False

    # 获取配置参数
    canvas_width = canvas_config.get('width', 1242)
    canvas_height = canvas_config.get('height', 1660)
    margin = defaults.get('margin', 40)
    gap = defaults.get('gap', 20)
    bg = parse_color(bg_color) if bg_color else parse_color(defaults.get('background', 'white'))

    left_count = custom_left if custom_left else layout_config.get('left', {}).get('count', 9)
    right_count = custom_right if custom_right else layout_config.get('right', {}).get('count', 3)
    left_width_max = layout_config.get('left', {}).get('width_max', 280)

    # 创建画布
    canvas = Image.new('RGB', (canvas_width, canvas_height), bg)

    # 获取所有图片
    images = sorted([f for f in os.listdir(input_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    total_needed = left_count + right_count
    if len(images) < total_needed:
        print(f"错误：需要至少 {total_needed} 张图片，当前只有 {len(images)} 张")
        return False

    # 可用区域
    content_width = canvas_width - margin * 2
    content_height = canvas_height - margin * 2

    # 左侧尺寸
    left_width, left_height = calculate_thumb_size(left_count, content_height, gap)
    left_width = min(left_width, left_width_max)

    # 右侧尺寸
    right_x = margin + left_width + gap
    right_width = canvas_width - right_x - margin
    right_height = (content_height - (right_count - 1) * gap) // right_count

    # 粘贴左侧缩略图
    for i in range(left_count):
        img_path = os.path.join(input_dir, images[i])
        try:
            img = Image.open(img_path).convert('RGB')
            y = margin + i * (left_height + gap)
            paste_image(canvas, img, margin, y, left_width, left_height)
        except Exception as e:
            print(f"警告：无法读取图片 {images[i]}: {e}")

    # 粘贴右侧大图
    for i in range(right_count):
        img_path = os.path.join(input_dir, images[left_count + i])
        try:
            img = Image.open(img_path).convert('RGB')
            y = margin + i * (right_height + gap)
            paste_image(canvas, img, right_x, y, right_width, right_height)
        except Exception as e:
            print(f"警告：无法读取图片 {images[left_count + i]}: {e}")

    # 保存
    canvas.save(output_path, 'PNG')
    print(f"已生成：{output_path}")
    return True


def render_top_bottom_with_title(input_dir, output_path, config, layout_name, title_text=None):
    """上下双图 + 标题布局"""
    from PIL import ImageDraw, ImageFont

    canvas_config = config.get('canvas', {})
    defaults = config.get('defaults', {})
    layout_config = config.get('layouts', {}).get(layout_name)

    canvas_width = canvas_config.get('width', 1242)
    canvas_height = canvas_config.get('height', 1660)
    bg = parse_color(defaults.get('background', '#f3dfc6'))

    margin = 40  # 四周留白
    title_height = layout_config.get('title_height', 120)
    layer_gap = layout_config.get('layer_gap', 40)

    # 创建画布
    canvas = Image.new('RGB', (canvas_width, canvas_height), bg)

    # 获取所有图片
    images = sorted([f for f in os.listdir(input_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    if len(images) < 2:
        print(f"错误：需要至少 2 张图片，当前只有 {len(images)} 张")
        return False

    # 内容区域
    content_width = canvas_width - margin * 2
    content_top = margin
    content_bottom = canvas_height - margin
    content_height = content_bottom - content_top

    # 文字居中在整张图的垂直中央，两张图与文字间距相同
    # 布局：上图片 + gap + 文字 + gap + 下图片
    # 文字高度由字号决定（先用60pt估算），gap固定
    # 反推：img_height * 2 + text_bbox.height + gap * 2 = content_height
    # 先用默认字体估算文字高度
    try:
        font_est = ImageFont.truetype("msyh.ttc", 60)
    except:
        try:
            font_est = ImageFont.truetype("simhei.ttf", 60)
        except:
            font_est = ImageFont.load_default()
    est_bbox = font_est.getbbox("示例文字")
    est_text_h = est_bbox[3] - est_bbox[1]

    gap = layer_gap
    img_height = (content_height - est_text_h - gap * 2) // 2
    img_top = content_top
    text_top = img_top + img_height + gap
    img_bottom = text_top + est_text_h + gap

    # 上方图片
    img1 = Image.open(os.path.join(input_dir, images[0])).convert('RGB')
    paste_image(canvas, img1, margin, img_top, content_width, img_height)

    # 绘制标题文字（居中）
    if title_text:
        draw = ImageDraw.Draw(canvas)
        try:
            font_size = 60
            font = ImageFont.truetype("msyh.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("simhei.ttf", font_size)
            except:
                font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), title_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_x = (canvas_width - text_w) // 2
        # 文字垂直居中于预估位置
        text_y = text_top + (est_text_h - text_h) // 2

        draw.text((text_x, text_y), title_text, fill=(0, 0, 0), font=font)

    # 下方图片
    img2 = Image.open(os.path.join(input_dir, images[1])).convert('RGB')
    paste_image(canvas, img2, margin, img_bottom, content_width, img_height)

    canvas.save(output_path, 'PNG')
    print(f"已生成：{output_path}")
    return True


def main():
    config = load_config()

    parser = argparse.ArgumentParser(description='PPT 排版图片生成器')
    parser.add_argument('input_dir', help='输入图片目录')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('-l', '--layout', default='layout1',
                       help='布局类型 (layout1, layout2, layout3...)')
    parser.add_argument('-b', '--bg', '--background', dest='bg',
                       help='背景色 (颜色名或HEX，如 white, #F5F5F5)')
    parser.add_argument('--left', type=int,
                       help='左侧图片数量（覆盖配置）')
    parser.add_argument('--right', type=int,
                       help='右侧图片数量（覆盖配置）')
    parser.add_argument('--list', action='store_true',
                       help='列出所有可用布局')
    parser.add_argument('-t', '--title', dest='title',
                       help='标题文字（用于 layout3）')

    args = parser.parse_args()

    # 列出布局
    if args.list:
        if config and 'layouts' in config:
            print("可用布局：")
            for key, val in config['layouts'].items():
                print(f"  {key}: {val.get('name')} - {val.get('description')}")
        else:
            print("未找到布局配置文件")
        return

    if not config:
        print("错误：未找到 layouts.json 配置文件")
        return

    # 生成输出路径
    if not args.output:
        base = os.path.basename(args.input_dir.rstrip('/\\'))
        args.output = os.path.join(args.input_dir, f'output_{args.layout}.png')

    # 根据布局类型选择渲染函数
    layout_type = config.get('layouts', {}).get(args.layout, {}).get('type', 'left_right')

    if layout_type == 'three_tier':
        render_three_tier(args.input_dir, args.output, config, args.layout)
    elif layout_type == 'top_bottom_with_title':
        render_top_bottom_with_title(args.input_dir, args.output, config, args.layout, args.title)
    else:
        render_layout(args.input_dir, args.output, config, args.layout,
                      args.bg, args.left, args.right)


if __name__ == '__main__':
    main()