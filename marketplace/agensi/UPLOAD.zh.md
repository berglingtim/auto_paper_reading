# Agensi 上传说明

本次交付的是 **适配包 v0.6.0**，调用公开工具包 **v0.6.0**。项目继续使用 MIT。

## 上传哪个文件

只上传 `auto-paper-reading-agensi-v0.6.0.zip`。

从 [GitHub v0.6.0 Release](https://github.com/berglingtim/auto_paper_reading/releases/tag/v0.6.0)
下载这个附件即可。GitHub 自动提供的 Source code ZIP 包含整个工具包，不是市场上传包。
本地重建命令：`python tools/package_agensi.py`，默认输出到 `output/agensi-v0.6.0/`。
仓库中的 `skills/auto-paper-reading/` 是正式维护的技能内容，
`marketplace/agensi/` 是商品资料；打包采用固定文件清单。

包内只有一个 `SKILL.md`、两个文本参考文件和 MIT `LICENSE`。它通过用户已安装的
GitHub 工具包完成解析、排版与检查，不包含运行时、依赖目录、论文或案例二进制文件。
英文商品文案和本说明留给你填写页面，不放进供 Agent 加载的包。

## 填写页面

1. 登录 Agensi，启用 Creator Mode 并完善作者资料。
2. 打开[提交页面](https://www.agensi.io/dashboard/submit)，上传上述 ZIP。
3. 打开同目录 `listing.en.md`，按同名字段复制：Name、Summary、Description、
   See it in action、Compatibility note、Categories、Tags、Use cases、
   Permissions、Limitations、FAQ、Documentation URL。
4. 版本填 **0.6.0**。工具包版本 **v0.6.0** 已在介绍中说明。若页面自动填了机器名称
   `auto-paper-reading`，将展示名称改成文案中的名称。名称是否可用由平台检查。
5. 定价由你选择；本次没有替你设置价格或承诺付费服务。
6. 检查自动识别的文件、终端和联网权限；预览后提交审核。

分类顺序建议按文案：Research & Analysis → Education & Learning → Productivity。
封面和截图可另加；本次的上传包不依赖它们。

## 平台适配范围

Agensi 按需发送文本文件，包内文件不等于本地项目目录。因此适配包通过文件读取接口
加载说明，再调用**独立安装的公共 GitHub 项目**。用户需要具备终端、文件、联网和看图
能力的 Agent，以及 Python、Node.js 和 LibreOffice；商品页已明确披露。
参见[加载规则](https://www.agensi.io/docs/how-agents-load-skills)及
[打包规则](https://www.agensi.io/docs/packaging)。

这套外部工具包方案已做本地验证，但**尚未经过 Agensi 审核或线上加载验证**。
上传后如果平台不接受这种依赖形式，应按其反馈调整，不绕过审核。上线后的首次试用，
请检查参考文件读取、工具包定位、Word 生成和 PDF 预览是否都能实际执行。

v0.6.0 将 Office 转换放在系统临时目录的短路径下执行，再把验证后的 PDF 安全写回
目标目录；保留函数名正体和变量斜体，并检查实际 PDF 的字体表现。
运行环境需要允许读写系统临时目录和启动本地转换器。
自动公式审计仍需配合逐页视觉检查，不能代替对论文内容的核实。

## 文案中的案例和许可

- Attention 案例链接指向 GitHub 中已发布的中英文成品，不冒充 Agensi 的成功运行记录。
  历史 PDF 是 WPS 快照；新适配包默认使用 LibreOffice，文案已解释。
- 项目原创内容和适配说明保持 MIT；依赖与论文图表仍按各自许可证使用。
  PyMuPDF 的许可另见[官方说明](https://pymupdf.readthedocs.io/en/latest/about.html)。
- 若平台协议给买家的默认限制与公开 MIT 授权如何共同适用不清楚，向平台确认；
  不要在商品页额外承诺“独占”“禁止复制”或“全部依赖均为 MIT”。

## 检查记录

`PACKAGE.json` 记录打包清单与校验结果，`SHA256SUMS.txt` 提供交付文件校验值。
Release 说明提供验证结果摘要；原始测试日志、预览和调试记录仅在本地保留。
这些本地验证不等于平台审核通过。

打包与字段规则核对日期：**2026-10-30**。
页面字段参见[官方提交说明](https://www.agensi.io/docs/submit-on-the-website)。
