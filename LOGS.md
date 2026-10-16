# 更新日志

版本规则：主版本.次版本.修订号；大更新（新功能/结构变化）本地 git 提交并记录版本号。

---

## v0.1.20（2026-10-16）docx 格式规范升级：TNR 正体 + 公式变量斜体 + 表格小五 + 参考文献六号

**背景**：用户明确新的排版要求：英语字母和数字一律 Times New Roman（正体），
只有公式中的变量采用斜体，其他情况不做改变；表格中的文字小五；参考文献六号。

**本次改动**
- `tools/build_docx.js`：正文/标题中的西文与数字由斜体改为 **Times New Roman 正体**
  （移除 latin run 的 italics，斜体仅保留在 OMML 公式变量上）；
  新增 `S_TABLE`（小五 9pt）与 `S_REFS`（六号 7.5pt）常量；
  整节标题匹配「参考文献/References」时正文按六号渲染
- `src/auto_paper_reading/omml.py`：每个数学 run 显式加 `w:rPr/w:rFonts`
  Times New Roman（ascii/hAnsi），公式变量斜体由 OMML 默认数学样式保留
- `SKILL.md` / `README.md`：格式规范表更新（封面西文改 TNR 正体；新增表格小五、
  参考文献六号两行；新增「仅公式变量斜体」规则）
- 重新生成 OpenSDI 讲解 docx 并全量复验
- 验证：22 测试通过；48 公式 `verify_math.py` 通过；WPS 渲染 15 页抽验封面与公式页
  （西文正体、公式变量斜体、无主题蓝）；docx XML 审计：普通 run 0 个斜体标记、
  4167 处 ascii 字体全为 Times New Roman、349 个数学 run 全部带 TNR 字体声明

---

## v0.1.19（2026-10-16）第四篇论文交付：OpenSDI（CVPR 2025）

**背景**：用户指定讲解 CVPR 2025 论文 OpenSDI: Spotting Diffusion-Generated Images
in the Open World（西安交大+南安普顿+哈工大）。论文 PDF 从 CVF Open Access 下载入库
`papers/OpenSDI.pdf`（11 页）。

**本次改动**
- 新增完整讲解 docx（`output/opensdi/OpenSDI/讲解_OpenSDI_ ...docx`，15 页）：
  - 五部分结构：1 基础知识（8 点：扩散模型与 T2I / 检测与定位两类任务 / CLIP / MAE /
    Prompt Tuning / 自注意力与交叉注意力 / FPN / 域内与跨域泛化，每点含「为什么有效+例子+本文用法」）
  - 2 方法灵感与发表期刊（OpenSDI 三设定配 Figure 1；现有数据集局限配 Table 1 原表；
    OpenSDID 构建流程配 Figure 2 + Table 2 原表）
  - 3 方法（SPM 框架 + Prompting/VCA/TVCA/VSA/FPN 与损失/训练配置，配 Figure 3 架构图逐块讲解）
  - 4 变换过程（按「兵分两路→Prompting→VCA 逐层→FPN→TVCA→VSA 聚合」六步数据流，
    形状/通道/注意力 QKV 来源逐步展开，复用 Figure 3 对着箭头走）
  - 5 创新点与借鉴经验（定性 Figure 4 + 定位 Table 3 / 检测 Table 4 / 消融 Table 5 /
    鲁棒性 Figure 5 全部原表原图嵌入 + 逐表读法讲解；另设「局限与展望」小节）
  - 48 个 OMML 公式（V_c∈R^{M×D}、VCA 注意力 G^l=Softmax(QK^T/√d)V、残差 V_m^{l+1}=V_m^l+G^l、
    M_fake/M_real∈R^{H×W}、V_cls={v^l_cls}_{l∈L}、L=L_CE+L_BCE+L_EDG 等）
- 配图裁剪：论文为双栏 CVF 版式，自动提取效果差（MaskCLIP 架构图被切成碎片、
  Figure 5 混入图注、Table 1-5 全部漏检），改为按渲染页人工框选坐标后 pymupdf 重裁
  （图 200dpi / 原表 300dpi），10 张图逐张视觉核验
- 修正解析器元数据：`paper.json` 期刊被误提取为 CVF 开放获取声明页脚，手工补正为
  CVPR 2025 / 2025 及作者单位
- 撰写中途修复 content.json LaTeX 反斜杠转义问题（公式命令在 JSON 中未双重转义），
  并规范化为可解析状态
- 验证：结构校验通过（170 段、10 图）；WPS 无头渲染 15 页预览逐页视觉核验
  （无乱码、无主题蓝、图片完整、公式原生渲染）；`verify_math.py` 48 公式全部通过

---

## v0.1.18（2026-10-16）安全加固与代码质量整理

**背景**：v0.1.17 之后一批代码审查改进在工作区未提交、未记录，本次补齐记录并同步版本号。

**本次改动**
- `llm.py`：API key 解析改为**环境变量优先**（config.json 明文 key 仅作回退并告警，
  提示泄露风险）；`chat_vision` 增加图片类型白名单（.png/.jpg/.jpeg/.webp）、
  存在性与大小校验（单张 20MB 上限）
- `figures.py`：`extract_figures` 增加输入校验（非 PDF / 文件不存在直接报错），
  输出目录与 PDF 路径统一 resolve
- `parser/convert.py`：`find_wps_convert` 查找结果**进程内缓存**（避免每次转换重复扫盘），
  清理冗余的 office6 直接判断分支（循环已覆盖）
- `explain.py`：LLM 返回体积上限 2MB（防异常大响应占内存），并校验顶层必须含 `sections`
- `tools/verify_math.py`：目标目录越界防护（解析后必须在项目目录内），
  公式关键符号检查表 KEY 字典重构为 if 链（检查语义等价）
- 测试：`pytest.ini` 增加 `pythonpath = src`，删除 conftest 与各测试文件里的
  `sys.path.insert` hack（统一由 pytest 提供 src 包导入路径）
- `src/auto_paper_reading/__init__.py`：`__version__` 从 0.1.0 同步为 0.1.18

**验证**：22 个测试通过；`git add -A` 后全量提交。

---

## v0.1.17（2026-08-14）第三篇论文交付：ConvNeXt（CVPR 2022）

**背景**：用户要求用项目管线讲解 `papers/convNeXt.pdf`——A ConvNet for the 2020s（Meta AI/FAIR + UC Berkeley，CVPR 2022）。

**本次改动**
- 新增完整讲解 docx（`output/convnext/convNeXt/讲解_A ConvNet for the 2020s.docx`，14 页）：
  - 五部分结构：1 基础知识（6 点：ConvNet 与归纳偏置/ResNet 残差/depthwise 卷积与空间通道分离/倒置瓶颈/BN vs LN/ViT 与 Swin，每点含"为什么有效+例子"）
  - 2 方法灵感与发表期刊 / 3 方法（现代化路线图 5 组改造逐步讲解，配 Figure 2 重裁去串版正文、Figure 3、Figure 4）
  - 4 变换过程（224×224×3 → 56×56×96 → … → 7×7×768 数据流逐 stage/block 内五步讲解；说明无注意力机制、以空间/通道分离混合作答）
  - 5 创新点与借鉴经验（实验结果直接调用论文原表 Table 1/3/4 高清裁剪 300dpi + 逐表读法讲解）
  - 14 个 OMML 公式（残差、LN、FLOPs 对比、block 结构等）
- 修正解析器元数据：`paper.json` 标题误提取为 arXiv 页眉（导致 docx 文件名异常），手工补正为 `A ConvNet for the 2020s` / CVPR 2022 后重新生成
- 验证：结构校验通过（129 段、6 图）；WPS 无头渲染 14 页预览逐页核验（无乱码、无主题蓝、图片完整、公式原生渲染）；`verify_math.py` 全部公式符号通过

---

## v0.1.16（2026-08-10）第二篇论文交付：FakeXplain（ICLR 2026）

**背景**：用户提供新论文练手——FakeXplain: AI-Generated Image Detection via Human-Aligned Grounded Reasoning（ICLR 2026，上海交大+蚂蚁）。

**本次改动**
- 新增 `papers/FakeXplain.pdf` + 完整讲解 docx（`output/fakexplain/FakeXplain/讲解_....docx`，11 页）：
  - 五部分结构：1 基础知识（8 点：AIGI 任务/MLLM/幻觉/bbox 与 IoU/SFT/GRPO 奖励/CoT 结构化输出/人工标注数据集，每点含"为什么有效+例子"）
  - 2 方法灵感 / 3 方法（数据集构建 + SFT + 三重奖励 + pGRPO，配 Figure 1/2/4 原图重裁）
  - 4 变换过程（推理数据流 <think>/<tag>/<verdict> + 训练阶段学习变化，配 Figure 5）
  - 5 创新点（实验结果直接用论文原表 Table 1-4 高清裁剪 + 逐表讲解，配 Figure 10）
  - 23 个 OMML 公式（IoU、三重奖励、ω_G(t) 等）
- 修复 `omml.py`：`\ `（转义空格）此前渲染成字面反斜杠，现正确渲染为空格
- `tools/verify_math.py` 参数化：`python tools/verify_math.py [论文输出目录]`，支持任意论文自检
- 验证：22 测试通过；IAPL 与 FakeXplain 双论文公式自检通过；视觉核验关键页

---

## v0.1.15（2026-08-10）基础知识讲解升级：每个知识点补"为什么有效 + 举个例子"

**背景**：用户要求基础知识讲解增加"为什么能达到这样的效果"的详细解释，太抽象的要举例子。

**本次改动**
- 重写第 1 章"基础知识讲解"8 个知识点，每点改为三段式：
  ① 概念 → ② **为什么能达到这样的效果**（机制解释：对比学习为何有效、注意力动态路由、
  冻结+适配为何省且稳、熵最小化为何让模型"想清楚"、高频指纹为何机器可见等）
  ③ **举个例子**（狗/猫图文对、猫耳朵与猫尾巴、眼科医生戴特制眼镜、考生便签、
  多角度眯眼看照片、发丝网格伪影、方言听力等具体类比与数字）
- `SKILL.md` 写作规范更新：基础知识每点必须含"概念 / 为什么有效 / 例子"三段
- 验证：13 页渲染、视觉确认第 1 页三段式排版正常、37 公式自检通过、22 测试通过

---

## v0.1.14（2026-08-10）项目文件夹整理

**本次改动**
- 清理过期产物：`output/_demo`（早期演示）、`讲解_..._v2.docx` 与 `_v2.pdf`（文件占用时产生的旧版）、
  `figures/fig_05_p4.png`（误裁剪的正文杂图）、`.pytest_cache/`、`tests/.pytest_tmp/`
- `.gitignore` 增加 `.pytest_cache/`
- `README.md` 重写，与当前功能对齐（五部分结构、三级编号、黑色字体、公式 WPS 渲染、
  论文原表讲解、verify_math 自检、目录结构、依赖）
- 重新生成最终 docx：135 段、8 张嵌入图（4 配图 + 4 原表）、11 页；37 公式自检通过、22 测试通过

---

## v0.1.13（2026-08-10）新增"基础知识讲解"部分（前置知识逐点讲解）

**背景**：用户要求"在最开始加入一个基础知识讲解部分，讲论文前置知识，一个小点一个小点讲解"。

**本次改动**
- content.json 新增第 1 章"基础知识讲解"，8 个知识点（二级标题 + 简短讲解，均注明本文用法）：
  1.1 CLIP / 1.2 ViT 与 token / 1.3 注意力机制（Q/K/V）/ 1.4 冻结骨干 + Adapter/LoRA /
  1.5 Prompt Learning / 1.6 测试时自适应与熵最小化 / 1.7 高频信号与 DCT / 1.8 seen vs unseen 任务设定
- 后续章节自动顺延编号：2 方法灵感 / 3 方法 / 4 变换过程 / 5 创新点
- `SKILL.md` 写作规范更新为五部分结构，开头"基础知识讲解"逐点讲前置知识
- 验证：11 页渲染、视觉确认第 1 页知识点排版正常、37 公式自检通过、22 测试通过

---

## v0.1.12（2026-08-10）实验结果直接调用论文原表

**背景**：用户要求"实验结果请直接调用论文的表格进行讲解"。

**本次改动**
- 从论文 PDF 高清裁剪（300dpi）Table 1-4 原表图片（含表头、方法行、Ours 蓝色高亮），
  作为 figure 嵌入 docx（id: table_1~table_4）
- content.json 4.2 实验结果佐证：插入 4 张原表 + 逐表讲解（怎么读表、Ours 数值、
  与最强基线差距、跨生成器稳定性）；保留原有文字总结
- `SKILL.md` 写作规范新增：实验结果必须直接调用论文原表（裁剪 + 逐表讲解），不只用文字
- 验证：8 张嵌入图（4 配图 + 4 原表）、9 页渲染、视觉确认 Table 1-3 页排版正常、
  37 公式自检通过、22 测试通过

---

## v0.1.11（2026-08-10）三级编号标题（1 / 1.1 / 1.1.1）+ 输出文件被占用自动换名

**背景**：用户要求"采取三级标题，不然讲得太乱"，即 1 / 1.1 / 1.1.1 细分。

**本次改动**
- `tools/build_docx.js`：标题**自动编号**（一级 1、二级 1.1、三级 1.1.1），content.json 只写标题文字
- `content.json` 重构细分：
  - 第 1 节拆二级：1.1 发表信息 / 1.2 背景与动机 / 1.3 现有方法的局限 / 1.4 灵感来源
  - 第 2 节：2.1 总体设计 / 2.2 MLP Adapter / 2.3 Learnable Token / 2.4 Image-Adaptive Prompt
    （下含 2.4.1 TTT / 2.4.2 CIL / 2.4.3 融合）/ 2.5 损失与推理
  - 第 3 节：3.1 逐步变换详解（3.1.1~3.1.6 六步）/ 3.2 数据流总结
  - 第 4 节：4.1 核心创新点 / 4.2 实验结果佐证 / 4.3 可借鉴经验 / 4.4 局限提示
- `cli.py`：输出 docx 被占用（如正被 WPS 打开，EBUSY）时自动改用 `_v2`/`_v3` 文件名重试
- `SKILL.md`：说明标题自动编号规则，并建议用足三级标题细分

**验证**：标题编号 1~4 / 1.1~4.4 / 2.4.1~3.1.6 全部正确；37 公式自检通过；22 测试通过；8 页渲染。

---

## v0.1.10（2026-08-10）交付前 LaTeX 渲染自检流程

**背景**：用户要求"交付时自己再验证一遍"LaTeX 渲染。

**本次改动**
- 新增 `tools/verify_math.py`：交付自检脚本——逐一检查 content.json 中每个公式的关键符号
  是否出现在 WPS 渲染 PDF 的文字层；`|`/`∑` 等被渲染成矢量图形的符号回退检查 docx 的 OMML 结构
- content.json 微调：第三节步骤正文去掉重复的步骤标题前缀（6 处）、`L = L_cls + L_aux`→公式、
  正文漏转的 `C_f`/`C_g`（2 处）；断言 $ 外无 `^`/下划线伪数学/`****`
- `SKILL.md` Step 6 增加硬性要求：交付前必须 `--verify` 渲染 + 自动化自检 + 视觉抽验公式

**验证**：37 个公式全部通过自检；22 个测试通过；7 页渲染正常。

---

## v0.1.9（2026-08-10）SKILL.md 强调字体统一黑色

**本次改动**：SKILL.md 三处强调"全文档字体统一黑色（含标题/正文/公式/图注，禁止主题蓝）"——
格式规范、Step 5 校验清单、常见问题表（含"标题出现蓝色"的处理说明，注明 v0.1.8 已处理勿回退）。

---

## v0.1.8（2026-08-10）标题主题蓝 → 纯黑

**背景**：用户反馈"组件二：Learnable Token（固定参数）"这类标题仍是蓝色。
**根因**：docx-js 内置 Heading 样式自带主题蓝（accent color），覆盖了默认黑色。

**本次改动**
- `tools/build_docx.js`：所有 run 显式加 `color: 000000`（run 级颜色优先于样式色）；
  并覆盖 Heading1-3/Title 样式为黑色
- 验证：docx run 颜色 1976/1981 为黑色；WPS 渲染 PDF 中标题 span 颜色均为 #000000

---

## v0.1.7（2026-08-10）补齐漏转公式 + 修复加粗嵌套

**背景**：用户反馈 `P_o^(j-1)`、`Wd ∈ R^{D×D̂}` 未渲染成公式。经扫描确认：这两处当初转换
content.json 时被遗漏，仍是带 `^` 的纯文本（并非缓存问题）；另发现 3 处加粗标记嵌套损坏
（`****CLIP** **ViT-L/14****`、`****Image-Adaptive Prompt** Learning**`，源于术语列表重叠）。

**本次改动**
- content.json 补齐：`$W_d \in \mathbb{R}^{D\times \hat{D}}$`、`$W_u \in \mathbb{R}^{\hat{D}\times D}$`、`$P_o^{(j-1)}$`
- 修复 3 处嵌套加粗标记 → 单层 `**CLIP ViT-L/14**`、`**Image-Adaptive Prompt Learning**`
- 断言校验：$ 配平（66）、$ 外无 `^`、无 `****`、33 个公式全部可解析
- 验证（视觉裁剪确认）：`W_d ∈ R^{D×D̂}`（含下标与 D 帽子）、`P_o^{(j-1)}`、`P_i^{(j)} = α^{(j)} ⊙ P_o^{(j-1)} + T^{(j)}` 均正确渲染

---

## v0.1.6（2026-08-10）修复公式渲染：移除非法 m:group + 字体统一黑色

**背景**：用户反馈"有些公式渲染有问题、有些没渲染成功"，要求用视觉探查；并要求字体全部黑色。

**根因（视觉+PDF 文字层定位）**：OMML 规范中没有 `<m:group>` 元素，WPS 直接丢弃其内容——
所有 `{...}` 分组（上下标、\frac、\sum 上下限、\left...\right 内部）整体消失，
表现为 "T∈"（缺上标）、"2||"（定界符内容丢失）、"L="（缺下标）等。

**本次改动**
- `omml.py` 解析器重构：`{...}` 组不再包装为 m:group，而是展开为父容器
  （m:e / m:num / m:den / m:sub / m:sup / oMath）的直接子元素；函数名（log 等）改用正体样式
- `tools/build_docx.js`：默认样式显式 `color: 000000`，全文档（含公式）字体统一黑色
- 验证：WPS 渲染 PDF 文字层出现 ∈/⊙/α/σ/× 等符号；视觉确认
  `T^(j) ∈ R^(2×D)`、`P_i^(j) = α^(j) ⊙ P_o^(j-1)`、`L_avg`、`p=1/m Σ σ(z_k)` 等公式渲染完整；
  30 个 OMML 注入、22 个测试全过

---

## v0.1.5（2026-08-10）公式改为 WPS 原生渲染：LaTeX → OMML

**背景**：用户要求公式用 WPS 渲染（此前是 `α^(j)` 这类纯文本，WPS 不会渲染成公式）。

**本次改动**
- 新增 `src/auto_paper_reading/omml.py`：LaTeX → OMML（Office Math）转换器，支持上下标、\frac、\sum/\prod/\int、\sqrt、\left...\right、希腊字母、\mathbb、函数与常用符号
- `tools/build_docx.js`：`$...$` 公式提取为占位 run
- `cli.py`：docx 生成后把占位 run 替换为 OMML 元素（python-docx 层完成，不调用任何 Office 软件）
- `output/iapl/IAPL/content.json`：30 处公式改为 `$...$` LaTeX（Eq 1/2/6、熵损失、形状符号等）
- 新增 `tests/test_omml.py`（10 个用例）
- `SKILL.md`：content.json 增加 `$...$` 公式语法说明

**验证**：30 个 OMML 公式注入成功、占位清零、python-docx 树内 30 个 m:oMath 结构正确、格式审计 0 问题、78 段 4 图完整。测试共 22 个用例通过（含修复 `skip_ws` 空串死循环导致的 pytest 挂起；basetemp 配置移到 conftest）。

---

## v0.1.4（2026-08-10）docx 格式规范：黑体/宋体 + Times New Roman 斜体 + 三级标题

**背景**：用户明确生成 docx 的格式要求。

**本次改动**
- `tools/build_docx.js` 全面改造：
  - 西文/数字一律 **Times New Roman 斜体**（按字符类别切分 run，中文保持正体）
  - 一级标题黑体三号(16pt)、二级黑体四号(14pt)、三级黑体小四(12pt)、正文宋体小四(12pt)、图注 10.5pt
  - 正文专业术语支持 `**...**` 加粗标记；`{"type":"heading","level":2|3}` 二级/三级标题块
  - 修复封面标题 run 失效 bug（对象展开改显式 allBold 参数）
- `output/iapl/IAPL/content.json`：47 处专业术语加粗 + 二级/三级标题（方法部分按组件拆二级，变换过程按步骤拆三级）
- `SKILL.md`：content.json 新增 heading 块与加粗标记说明 + 格式规范表
- 验证：全文档 2197 个 run 审计 0 问题（全部 TNR、西文全斜体、字号分布正确）；78 段、5 图结构校验通过

---

## v0.1.3（2026-08-09）修改范围锁定工作区 + WPS 全部改为显式 opt-in

**背景**：用户明确"能修改的范围仅限本工作区"；且此前 360 对 kimi.exe 驱动 wps.exe 的行为误报（自动化办公软件属安全软件敏感行为）。

**本次改动**
- `parser/__init__.py`：`.doc/.docx` 解析默认拒绝调用 WPS，必须显式 `--allow-wps` 才走 `kwpsconvert.exe word2pdf` 无头转换，否则直接报错并提示
- `cli.py`：新增 `--allow-wps` 参数（默认关闭）；docx 阶段默认只做结构化校验（不调用 Office）
- `pytest.ini`：`basetemp` 收进工作区 `.pytest_tmp/`，测试不再写系统临时目录
- `SKILL.md`：写入"修改范围红线"（仅工作区）+ WPS 显式 opt-in 说明
- 测试：新增 `test_docx_requires_allow_wps`，共 12 个用例全部通过

**当前所有 WPS 调用点均为用户显式触发**：`.doc/.docx` 输入转换（--allow-wps）、预览渲染（--verify）。

---

## v0.1.2（2026-08-09）WPS 使用红线：默认流程不再调用 WPS

**背景**：用户反馈"别让 WPS 打开它不该打开的东西"——此前 `wps.exe /t` GUI 转换测试会真的在 WPS 里打开文档，且生成 docx 后自动调 WPS 转 PDF 渲染。

**本次改动**
- `cli.py`：docx 阶段默认只做**结构化校验**（python-docx + zipfile，不依赖任何 Office 软件）；视觉渲染预览改为显式 `--verify` 才执行
- 明确 WPS 使用红线：全流程仅允许无头的 `kwpsconvert.exe word2pdf`（不弹窗），用于 `.doc/.docx` 输入转换与显式 `--verify`；绝不调用 `wps.exe` 打开 GUI、绝不自动处理输出文件
- `SKILL.md`：Step 5 校验方式与 WPS 红线写入工作流文档

---

## v0.1.1（2026-08-09）修复配图裁剪 + 交付首篇论文讲解

**本次改动**
- `figures.py` 重写配图裁剪：
  - 用 `get_images() + get_image_rects()` 取图片真实放置位置，支持旋转/镜像图片（原 bbox 倒置导致漏检，如 IAPL 的 Figure 4 架构图）
  - 光栅区域按垂直/水平相邻合并（同一 Figure 的子图行自动合并，如 IAPL 的 Figure 2 t-SNE 三联图）
  - 矢量图（流程图/架构图）按图注定位 + 绘图对象并集裁剪，解决无嵌入图片的流程图漏检（如 IAPL 的 Figure 1/3）
  - 过滤压住正文文字的误框、越界矩形、整页背景图；每页缓存绘图对象避免重复解析
- `cli.py`：输出文件名净化（防路径逃逸）、node 子进程加 180s 超时、UTF-8 控制台输出
- 新增 `tests/test_figures.py`（bbox 规范化、区域合并、图注正则等纯函数测试）
- 测试：11 个用例全部通过

**交付**
- 首次完成真实论文讲解验收：`papers/IAPL.pdf`（AI 生成图像检测，arXiv 2508.01603）
  → 解析提取 6 张配图 → 视觉筛选 4 张关键图 → 撰写四部分图文讲解 →
  生成 `output/iapl/IAPL/讲解_....docx`（7 页，图文混排）→ WPS 转 PDF 渲染校验通过

---

## v0.1.0（2026-08-09）项目初始化：核心管线跑通

**本次改动**
- 建立项目结构：`src/auto_paper_reading` 核心包、`tools/build_docx.js` 排版脚本、`tests/`、`papers/`、`output/`
- 解析层（`parser/`）：`.pdf` 用 pymupdf 解析；`.doc/.docx` 经 WPS `word2pdf` 转 PDF 后统一走 PDF 管线；统一数据模型 `PaperDocument`/`FigureRef`
- 配图裁剪（`figures.py`）：光栅图直接读取裁剪 + 矢量图按图注（Figure N/图 N）定位裁剪；图注关联、页码/尺寸记录
- 讲解生成（`explain.py` + `llm.py`）：DeepSeek/Kimi/OpenAI 兼容的 LLM 客户端；四部分结构化讲解 prompt（方法灵感与期刊/方法/变换过程/创新点）
- docx 排版（`tools/build_docx.js`，基于 docx skill 的 docx-js）：中文微软雅黑、图文混排、图片按版心自适应缩放
- CLI（`run.py` → `cli.py`）：`prep`（解析裁剪）/`content`（视觉筛选+LLM 生成）/`docx`（排版+WPS 转 PDF 渲染校验）三阶段
- 工作流（`SKILL.md`）：Agent 讲解论文的完整流程（kimi-ai-hybrid vision 选图 → 撰写 content.json → 生成 docx → 校验 → 对话讲解）
- 测试：6 个用例全部通过（模型序列化、PDF 解析/裁剪/图注、WPS 转换、格式校验）

**验证**
- `python -m pytest tests/ -q` → 6 passed
- 端到端：样例 PDF → prep 提取 2 图（光栅+矢量）→ 构造 content.json → 生成图文 docx → WPS 转 PDF 渲染校验通过

**已知限制**
- 扫描版 PDF（无文字层）无法提取图注/文本，需 OCR
- 图注在上方的论文、双栏复杂版面可能裁剪不准，需人工/视觉复核
- 脚本模式的 `content`/`full` 阶段需配置 API key（`config.json` 或环境变量）
