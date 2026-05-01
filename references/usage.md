# PPT 排版图片生成器

将 PPT 导出的多张图片，自动排版成适合小红书等平台发布的拼接图片。

## 布局说明

### 布局一：左侧9缩略图 + 右侧3大图

```
┌──────────────────────────────────────┐  1242px 宽
│ ┌────┐   ┌────────────────────────┐ │
│ │ p1 │   │                        │ │
│ ├────┤   │       p10 大图          │ │
│ │ p2 │   │                        │ │
│ ├────┤   ├────────────────────────┤ │
│ │ p3 │   │                        │ │
│ ├────┤   │       p11 大图          │ │
│ │ p4 │   │                        │ │
│ ├────┤   ├────────────────────────┤ │
│ │ p5 │   │                        │ │
│ ├────┤   │       p12 大图          │ │
│ │ p6 │   │                        │ │
│ ├────┤   │                        │ │
│ │ p7 │   │                        │ │
│ ├────┤   │                        │ │
│ │ p8 │   │                        │ │
│ ├────┤   │                        │ │
│ │ p9 │   │                        │ │
│ └────┘   └────────────────────────┘ │
└──────────────────────────────────────┘
              1660px 高
```

- 整体尺寸：1242px 宽 × 1660px 高
- 边距：40px（四周留白，呼吸感）
- 图片间距：20px
- 背景色：#f3dfc6（默认暖米色）

## 配置文件

布局通过 `layouts.json` 管理，方便添加和修改：

```json
{
  "canvas": { "width": 1242, "height": 1660 },
  "defaults": {
    "margin": 40,
    "gap": 20,
    "background": "#f3dfc6",
    "left_count": 9,
    "right_count": 3
  },
  "layouts": {
    "layout1": { "name": "左侧9缩略图 + 右侧3大图", "left": { "count": 9 }, "right": { "count": 3 } },
    "layout2": { "name": "左侧6缩略图 + 右侧6大图", "left": { "count": 6 }, "right": { "count": 6 } },
    "layout3": { "name": "左侧4缩略图 + 右侧2大图", "left": { "count": 4 }, "right": { "count": 2 } }
  }
}
```

## 使用方法

```bash
# 列出所有布局
python ~/.claude/skills/dp-xhsppt-output_layout/ppt_layout.py --list

# 使用布局一（默认）
python ~/.claude/skills/dp-xhsppt-output_layout/ppt_layout.py "G:/PPT导出图片/"

# 指定布局
python ~/.claude/skills/dp-xhsppt-output_layout/ppt_layout.py "G:/PPT导出图片/" -l layout2

# 自定义背景色
python ~/.claude/skills/dp-xhsppt-output_layout/ppt_layout.py "G:/PPT导出图片/" -b "#f3dfc6"

# 自定义左右数量（覆盖配置）
python ~/.claude/skills/dp-xhsppt-output_layout/ppt_layout.py "G:/PPT导出图片/" --left 6 --right 6

# 指定输出路径
python ~/.claude/skills/dp-xhsppt-output_layout/ppt_layout.py "G:/PPT导出图片/" -o "G:/输出/result.png"
```

## 输入要求

- 图片格式：PNG、JPG、JPEG
- 图片命名：按顺序排列（如 1.png, 2.png, 3.png...）
- 图片比例：16:9 最佳