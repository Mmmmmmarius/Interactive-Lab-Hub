# Touch grass：草宠物与界面改版提案

状态：Marius 已于 11 月 2 日批准，正式界面已部署到 Pi。实际截图和检查见 [部署记录](_%E8%AF%81%E6%8D%AE/grass-ui/README.md)。下文保留原方案，作为这一轮设计依据。

[查看草宠物各状态的交互预览](UI%E9%A2%84%E8%A7%88/grass-states.html)。五档分数和六种运行状态采用同一个角色，点击宠物可切换台词，滑块可比较分档。

任务：T088。沿用 [Lab 5 产出卡](%E4%BA%A7%E5%87%BA%E5%8D%A1.md)。草宠物、按分数变化和 meme 文案来自 Marius 的本轮要求，以下造型、分档和具体文案已获 Marius 批准。

## 推荐方向

用一只表情很丰富、略带欠揍感的小草做主角。它像一个看完记录后忍不住吐槽的桌面宠物。整个界面保留英文，功能说明简洁，笑点集中在宠物和气泡里。

宠物暂称 **Grass bro**。身体是一小簇草，三片长叶作为头顶轮廓，配半睁的眼睛、小嘴、细手臂和短腿。保持同一个角色，通过眼神、姿势和叶片弯曲区分状态。

采用二维漫画风。草绿主体、深绿描边、浅蓝背景和少量明黄色强调。宠物、气泡和分数形成一个完整场景，下面接一行时间与采样信息，再接检测时间线。

### 分数与表现

分数继续表示桌前时长，越高越需要离开桌子。以下五档只是视觉分档，不改变计分公式。

| 分数 | 宠物表现 | 默认气泡 | 同档可替换文案 |
| --- | --- | --- | --- |
| 0–24 | 叶片舒展，双手放松，轻轻微笑。 | `we're chillin.` | `no roast today.`<br>`looking pretty chill, brother.` |
| 25–49 | 单侧挑眉，歪头看向分数。 | `locked in, huh?` | `interesting chair commitment.`<br>`the chair has your attention.` |
| 50–74 | 叉腰，用一片叶子指向自己。 | `touch some grass, brother.` | `i'm grass. i'm right here.`<br>`the chair can wait.` |
| 75–99 | 眼睛睁大，随后缓慢侧目，叶尖开始耷拉。 | `are we deadass rn?` | `bro. the chair isn't going anywhere.`<br>`outside is still a thing.` |
| 100 | 夸张地瘫坐，叶片垂下，举起小白旗。 | `bro is fully cooked.` | `the chair won.`<br>`touch some grass, brother. seriously.` |

每份报告先显示该档默认句。点击宠物才切换同档短句，并给一个短动作，避免网页自动刷新时不断换文案。点击不会改变分数、时长或报告。

低分只表示模型估计的桌前时间较少，不写成已经外出、运动或真实接触草地。高分是玩笑反馈，不给健康诊断。

## 页面与文案

桌面上，左侧是宠物与气泡，右侧是分数和时长。手机上按宠物、分数、时间线的顺序排列。宠物是首屏最大的视觉元素。

```text
Touch grass.                              Recorded day

Simulated day · 15-minute capture

  “bro is fully cooked.”                   Touch grass score
                                           100 / 100
       [Grass bro 瘫坐举旗]                 Higher = more desk time.

Simulated desk time: 552 min                30 photos

The receipts
[检测时间线与清晰的文字图例]

Show the receipts: photos + original Qwen answer
```

上图的数据来自已保存的第二轮重分析结果，仅用于说明新布局。它是 15 分钟采集所对应的模拟日，不能写成真实全天记录。

| 当前内容 | 建议内容 | 保留的功能说明 |
| --- | --- | --- |
| 主标题固定介绍作品 | 根据有效报告显示对应档的宠物气泡。 | `Touch grass score` 和 `Higher = more desk time.` 常驻。 |
| 等待开始 | `ready when you are, brother.` | 明确提示按 Mini PiTFT 按钮开始采集。 |
| 采集中 | `gathering the receipts.` | 显示真实采样数量、剩余时间和当前模式。 |
| 采集结束 | `the receipts are in.` | 明确提示再次按 Mini PiTFT 按钮开始分析。 |
| 分析中 | `let me cook.` | 显示正在读取照片或估算时间，不伪造完成百分比。 |
| 检测记录区标题 | `The receipts` | 图例仍用 `Person detected`、`No person detected` 和 `Unknown`。 |
| 折叠证据入口 | `Show the receipts: photos + original Qwen answer` | 保留原图、原始时间戳和未经改写的模型回答。 |
| 运算校验失败 | `that math ain't mathing.` | 说明报告未通过校验、原答已保存，以及如何重试。 |
| 设备断开 | `bro? you there?` | 明确显示 Pi 连接中断，提示检查电源与同一网络。 |

无报告、处理失败和离线都有独立状态，不用 0 分或低分宠物冒充成功。若保留离线前的旧报告，必须注明它是最后保存的结果。非运算类错误使用对应的真实说明，不套用运算失败文案。

主结果中的时间和分数来自 Qwen 的有效回答。宠物吐槽使用前端文案库，和模型的原始总结分开呈现。Qwen 原答及不确定性继续可查，模拟标记放在首屏常驻，不折叠。

### 视觉参数

| 用途 | 建议 |
| --- | --- |
| 页面背景 | 云白 `#F7FBFF`。 |
| 宠物场景 | 浅蓝 `#D9EEFF`。 |
| 草的主体 | 草绿 `#71C940`。 |
| 字体与轮廓 | 深绿 `#173A29`。 |
| 提示和少量细节 | 明黄 `#FFD65A`。 |
| 额外表情细节 | 粉色 `#EF8BB2`，仅少量使用。 |
| 标题 | 粗体圆润无衬线，优先本机 Arial Rounded MT Bold，回退 Trebuchet MS 和 sans-serif。 |
| 正文与数据 | Trebuchet MS，回退 Arial 和 sans-serif。正文保持 16px 起。 |
| 动作 | 切换报告时做一次短表情动作，点击宠物再回应。默认不持续抖动，不自动播放声音，尊重减少动态效果设置。 |

本地设计资料最初返回了偏儿童产品的软质三维风格和橙色方案，与本项目不符，未采用。方案改用二维漫画表情，只在宠物和气泡上强调轮廓，其余信息区保持简单。

## 实施与验收

批准后按以下顺序实施，预计 45–75 分钟。耗时包含浏览器检查和 Pi 部署，网络连接问题另计。

1. **制作角色和文案，约 15–25 分钟。** 用 SVG 表达同一只草的五种姿态，整理分数与运行状态文案。页面保留现有原生 HTML、CSS 和 JavaScript，不增加前端框架或在线素材依赖。
2. **接入现有报告，约 15–20 分钟。** 修改网页布局和状态渲染。只根据有效报告中的分数选择表情，继续原样使用 Qwen 给出的时长和分数。采样、模型输入和计算校验保持现有行为。
3. **检查、部署与记录，约 15–30 分钟。** 核对电脑和手机布局，检查各分档边界、无数据、分析中、错误与离线状态。保存旧界面后部署静态文件，用现有真实报告截图更新 README。

具体代码范围是 `Study HQ/Projects/INFO5345/Lab5/touch_grass/web/`，以及该目录新增的宠物资源。部署位置是 Pi 的 `/home/pi/touch-grass/web/`。本轮先改内网网页，Mini PiTFT 保留已有采集和处理功能。

验收要点：

- 分数 0、24、25、49、50、74、75、99、100 都落入正确档位。无效数值不会得到成功状态。
- 有效 0 分与没有结果明显不同。页面断开时显示离线信息。
- 当前真实报告的 552 模拟分钟与 100 分原样显示，宠物进入最高档。其他分档用明确标注的界面测试数据检查，不写成额外实验。
- 页面刷新不会反复重播动作。宠物能用鼠标、触屏和键盘操作。减少动态效果后仍可完整读懂状态。
- 375px、768px 和桌面宽度下没有横向溢出，正文和操作控件可读。
- README 说明这次界面迭代及 AI 协助，保留原始错误记录和模拟说明。现有 YOLO 预览不因静态界面更新而关闭。

### 网络表达核对

以下为资料外补充。来源用于核对语义和实际用法，不把改写文案宣称为网络原句，也不下载其中的人物图或 GIF。

- **touch grass**：用于让过度沉浸线上活动的人离开屏幕，属于非正式表达。本项目沿用用户给的 `touch some grass, brother.`。[BBC Learning English](https://downloads.bbc.co.uk/learningenglish/features/tews/231212_tews_touch_grass.pdf)。
- **deadass**：这里表示认真、当真，通常连写。[Dictionary.com](https://www.dictionary.com/culture/slang/deadass)。`are we deadass rn` 有可核对的实际反应图用例。[Tenor 用例](https://tenor.com/view/are-we-deadass-rn-are-we-deadass-gif-9230393179388786087)。
- **locked in**：指进入高度专注的状态。中档的 `locked in, huh?` 是本项目的语气改写。[Know Your Meme](https://knowyourmeme.com/memes/when-you-gotta-lock-in)。
- **cooked**：可用于夸张地表示糟了、没救了。`bro is fully cooked.` 是拟定的最高档吐槽，不是对用户状态的事实判断。[Know Your Meme](https://knowyourmeme.com/memes/cooked-getting-cooked)。

执行结果：已按此方向完成。源码放在程序目录的 `ui/`，由 `build-ui.cjs` 生成 `web/` 中的三个静态文件。浏览器已核对当前模拟报告、短时测试报告、点击台词、键盘操作、自动刷新和四种屏幕宽度。当前浏览器启用了减少动态效果，点击时台词变化而动画关闭。采集、模型和实时 YOLO 均未重启。
