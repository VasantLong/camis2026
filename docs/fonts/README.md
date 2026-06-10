# 文档渲染字体

DOCX 模板引擎（docxtpl + LibreOffice）所需的中文字体。

## 字体清单

| 文件 | 字体名 | 用途 | 来源 |
|------|--------|------|------|
| `KaiTi_GB2312.ttf` | 楷体_GB2312 | 模板标签文字 | GB2312 标准字体，可自由分发 |
| `FangSong_GB2312.ttf` | 仿宋_GB2312 | 模板正文 | GB2312 标准字体，可自由分发 |
| ~~方正小标宋简体~~ | FZXiaoBiaoSong-B05S | 模板标题 | **商业字体，不入库** |

## 安装

```bash
cp KaiTi_GB2312.ttf FangSong_GB2312.ttf ~/.local/share/fonts/
fc-cache -fv
```

## 方正小标宋简体

该字体为方正字库商业字体，不在本仓库中分发。请从以下途径获取：
- 方正字库官网购买
- 项目维护者处获取副本

获取后将 `.ttf` 文件放入 `~/.local/share/fonts/`，执行 `fc-cache -fv` 即可。

缺少该字体会导致 DOCX 标题回退到系统默认字体，不影响功能但排版效果有差异。
