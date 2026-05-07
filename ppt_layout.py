#!/usr/bin/env python3
"""
PPT 排版图片生成器
支持通过 layouts.json 配置文件定义布局
批量生成全部布局，每种布局都用尽所有图片
"""

import os
import json
import argparse
from PIL import Image, ImageDraw, ImageFont

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'layouts.json')


import re


def extract_title_from_path(output_path):
    """从输出路径提取标题，格式：{主题}_{时间戳} -> {主题}"""
    folder = os.path.basename(os.path.dirname(output_path))
    return re.sub(r'[_\d]+$', '', folder)


def load_config():
    if os.path.exists(DEFAULT_CONFIG_PATH):
        with open(DEFAULT_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


# 可用背景色预设
BG_PRESETS = {
    'default': '#f3dfc6',    # 米黄色（默认）
    'pink': '#ffcbdf',       # 粉色
    'mint': '#e8f5f0',      # 薄荷绿
    'lavender': '#f0e6ff',   # 薰衣草紫
    'peach': '#ffe5d9',      # 蜜桃色
    'white': '#ffffff',      # 纯白
}

def parse_color(color_str):
    color_str = color_str.lower().strip()
    # 先检查预设颜色
    if color_str in BG_PRESETS:
        color_str = BG_PRESETS[color_str]
    color_map = {'white': '#FFFFFF', 'black': '#000000', 'red': '#FF0000',
                 'green': '#00FF00', 'blue': '#0000FF', 'yellow': '#FFFF00',
                 'gray': '#808080', 'grey': '#808080'}
    if color_str in color_map:
        color_str = color_map[color_str]
    if color_str.startswith('#'):
        hex_color = color_str[1:]
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b)
    return (255, 255, 255)


def paste_image(canvas, img, x, y, width, height):
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


def paste_image_fit(canvas, img, x, y, width, height):
    """Paste image maintaining aspect ratio, fit within the target area (letterboxed)."""
    img_ratio = img.width / img.height
    target_ratio = width / height
    if img_ratio > target_ratio:
        new_width = width
        new_height = int(width / img_ratio)
    else:
        new_height = height
        new_width = int(height * img_ratio)
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    paste_x = x + (width - new_width) // 2
    paste_y = y + (height - new_height) // 2
    canvas.paste(resized, (paste_x, paste_y))


def get_all_images(input_dir):
    return sorted([f for f in os.listdir(input_dir)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))])


def render_layout1(input_dir, output_path, images_subset, config, bg_color=None):
    """layout1：左侧9缩略图 + 右侧3大图"""
    canvas_config = config.get('canvas', {})
    defaults = config.get('defaults', {})
    canvas_width = canvas_config.get('width', 1242)
    canvas_height = canvas_config.get('height', 1660)
    margin = defaults.get('margin', 40)
    gap = defaults.get('gap', 20)
    bg = parse_color(bg_color) if bg_color else parse_color(defaults.get('background', 'white'))

    left_count = 9
    right_count = 3
    left_width_max = 280

    canvas = Image.new('RGB', (canvas_width, canvas_height), bg)
    if len(images_subset) < left_count + right_count:
        return False

    content_width = canvas_width - margin * 2
    content_height = canvas_height - margin * 2
    left_height = (content_height - (left_count - 1) * gap) // left_count
    left_width = min(int(left_height * 16 / 9), left_width_max)
    right_x = margin + left_width + gap
    right_width = canvas_width - right_x - margin
    right_height = (content_height - (right_count - 1) * gap) // right_count

    for i in range(left_count):
        img = Image.open(os.path.join(input_dir, images_subset[i])).convert('RGB')
        paste_image(canvas, img, margin, margin + i * (left_height + gap), left_width, left_height)
    for i in range(right_count):
        img = Image.open(os.path.join(input_dir, images_subset[left_count + i])).convert('RGB')
        paste_image(canvas, img, right_x, margin + i * (right_height + gap), right_width, right_height)
    canvas.save(output_path, 'PNG')
    return True


def render_layout2(input_dir, output_path, images_subset, config, bg_color=None):
    """layout2：三层瀑布流，每行N张"""
    canvas_config = config.get('canvas', {})
    defaults = config.get('defaults', {})
    canvas_width = canvas_config.get('width', 1242)
    canvas_height = canvas_config.get('height', 1660)
    bg = parse_color(bg_color) if bg_color else parse_color(defaults.get('background', '#f3dfc6'))

    canvas = Image.new('RGB', (canvas_width, canvas_height), bg)
    n = len(images_subset)
    if n == 0:
        return False

    margin = 60
    gap = 10
    layer_gap = 50
    bottom_margin = 60
    available_h = canvas_height - margin - bottom_margin - layer_gap * (3 - 1)
    top_height = int(available_h * 0.45)
    other_height = (available_h - top_height) // 2

    row_heights = [top_height, other_height, other_height]
    # 按行数均分图片
    row_counts = []
    idx = 0
    num_rows = 3
    for i in range(num_rows):
        count = (n - idx) // (num_rows - i) if i < num_rows - 1 else (n - idx)
        count = max(1, min(count, n - idx))
        row_counts.append(count)
        idx += count

    y = margin
    img_idx = 0
    for row_idx, count in enumerate(row_counts):
        if count == 0 or img_idx >= n:
            continue
        row_height = row_heights[row_idx]
        if count == 1:
            img = Image.open(os.path.join(input_dir, images_subset[img_idx])).convert('RGB')
            paste_image_fit(canvas, img, 0, y, canvas_width, row_height)
            img_idx += 1
        else:
            img_w = (canvas_width - gap * (count - 1)) // count
            for col in range(count):
                if img_idx >= n:
                    break
                img = Image.open(os.path.join(input_dir, images_subset[img_idx])).convert('RGB')
                paste_image_fit(canvas, img, col * (img_w + gap), y, img_w, row_height)
                img_idx += 1
        y += row_height + layer_gap

    canvas.save(output_path, 'PNG')
    return True


def render_layout3(input_dir, output_path, images_subset, config, bg_color=None, title=None):
    """layout3：上下排列，2张图，中间标题"""
    canvas_config = config.get('canvas', {})
    defaults = config.get('defaults', {})
    canvas_width = canvas_config.get('width', 1242)
    canvas_height = canvas_config.get('height', 1660)
    bg = parse_color(bg_color) if bg_color else parse_color(defaults.get('background', '#f3dfc6'))

    canvas = Image.new('RGB', (canvas_width, canvas_height), bg)
    if len(images_subset) < 2:
        return False

    margin = 40
    gap = 50
    content_width = canvas_width - margin * 2
    img_height = (canvas_height - margin * 2 - gap) // 2

    img1 = Image.open(os.path.join(input_dir, images_subset[0])).convert('RGB')
    paste_image_fit(canvas, img1, margin, margin, content_width, img_height)
    img2 = Image.open(os.path.join(input_dir, images_subset[1])).convert('RGB')
    paste_image_fit(canvas, img2, margin, margin + img_height + gap, content_width, img_height)

    # 中间标题
    draw_title = title or extract_title_from_path(output_path)
    if draw_title:
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc', 48)
        except Exception:
            try:
                font = ImageFont.truetype('C:/Windows/Fonts/simheibd.ttf', 48)
            except Exception:
                try:
                    font = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 48)
                except Exception:
                    font = ImageFont.load_default()
        title_y = margin + img_height
        draw = ImageDraw.Draw(canvas)
        bbox = draw.textbbox((0, 0), draw_title, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (canvas_width - text_w) // 2
        y = title_y + (gap - text_h) // 2
        draw.text((x, y), draw_title, font=font, fill=(60, 60, 60))

    canvas.save(output_path, 'PNG')
    return True


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description='PPT 排版图片生成器')
    parser.add_argument('input_dir', help='输入图片目录')
    parser.add_argument('-o', '--output', help='输出目录路径')
    parser.add_argument('-l', '--layout', help='布局类型 (layout1, layout2, layout3, all)')
    parser.add_argument('-b', '--bg', '--background', dest='bg', help='背景色')
    parser.add_argument('--list', action='store_true', help='列出所有可用布局')
    parser.add_argument('-t', '--title', dest='title', help='标题文字')
    args = parser.parse_args()

    if args.list:
        if config and 'layouts' in config:
            print("可用布局：")
            for key, val in config['layouts'].items():
                print(f"  {key}: {val.get('name')} - {val.get('description')}")
        return

    if not config:
        print("错误：未找到 layouts.json 配置文件")
        return

    images = get_all_images(args.input_dir)
    if not images:
        print("错误：目录中没有图片")
        return

    total = len(images)
    output_dir = args.output or args.input_dir
    os.makedirs(output_dir, exist_ok=True)

    # 批量生成布局
    def batch_generate(layout_name, imgs_per_output):
        """每imgs_per_output张图片生成一张排版图"""
        count = 0
        idx = 0
        while idx < total:
            batch = images[idx:idx + imgs_per_output]
            if len(batch) < 2:
                break
            output_path = os.path.join(output_dir, f'{layout_name}_{count+1:02d}.png')
            if layout_name == 'layout1':
                ok = render_layout1(args.input_dir, output_path, batch, config, args.bg)
            elif layout_name == 'layout2':
                ok = render_layout2(args.input_dir, output_path, batch, config, args.bg)
            else:
                title = args.title or extract_title_from_path(output_path)
                ok = render_layout3(args.input_dir, output_path, batch, config, args.bg, title)
            if ok:
                print(f"已生成：{output_path}")
                count += 1
            idx += imgs_per_output
        return count

    # 生成指定布局或全部
    if args.layout and args.layout != 'all':
        if args.layout == 'layout1':
            n = batch_generate('layout1', 12)
            print(f"\n共生成 {n} 张 {args.layout} 图片")
        elif args.layout == 'layout2':
            n = batch_generate('layout2', 5)
            print(f"\n共生成 {n} 张 {args.layout} 图片")
        elif args.layout == 'layout3':
            n = batch_generate('layout3', 2)
            print(f"\n共生成 {n} 张 {args.layout} 图片")
    else:
        print(f"\n=== 批量生成全部布局 ===")
        print(f"输入目录：{args.input_dir}")
        print(f"图片总数：{total}\n")

        n1 = batch_generate('layout1', 12)
        print()
        n2 = batch_generate('layout2', 5)
        print()
        n3 = batch_generate('layout3', 2)

        used1 = n1 * 12
        used2 = n2 * 5
        used3 = n3 * 2

        print(f"\n生成结果：")
        print(f"  layout1：{n1} 张，每张 12 图（用尽 {used1} 张，剩余 {total-used1} 张）")
        print(f"  layout2：{n2} 张，每张 5 图（用尽 {used2} 张，{('全用尽' if total-used2==0 else '剩余 '+str(total-used2)+' 张')}）")
        print(f"  layout3：{n3} 张，每张 2 图（用尽 {used3} 张，剩余 {total-used3} 张）")
        print(f"\n📁 文件路径：{output_dir}")


if __name__ == '__main__':
    main()
