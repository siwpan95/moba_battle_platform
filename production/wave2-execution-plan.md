# Wave 2 新增公有领域 IP — 执行方案

| 项 | 值 |
|---|---|
| 文档 ID | PROD-PLAN-002 |
| 作者 | 文策渊（design-strategist） |
| 日期 | 2026-08-06 |
| 审评强度 | **Full** |
| 上游依赖 | `design/gdd/content-expansion.md`（§2.4 Wave 2 框架）、`production/wave1-execution-plan.md`（§5 Wave 2 衔接）、`docs/architecture/content-pipeline-readiness.md`（§3 加载机制）、`tools/_archive/role_dnd_templates.json`（6 role × D&D 模板） |
| 数据基线 | Wave 1 完成后：1659 张卡、24 IP、LoL 172/172 全覆盖、σ≈26pp、card_id 已稳定为 `<game_id>:<hero_name>`、ADR-005 已实施（iter_card_files 统一扫描）、ATTRIBUTION.md + DISCLAIMER.md 已就位 |

---

## 0. 执行摘要（TL;DR）

**Wave 2 定位：公有领域 IP 的数量扩张（breadth），在 Wave 1 的质量地基上新增 7 个公有领域 IP、共 160 名英雄。**

核心策略：
- **100% 公有领域来源**——零版权敞口，与现有 24 个商业 IP 彻底隔离
- **复用 Wave 1 建立的 6 role × D&D 模板**——生成效率提升 65-75%，单英雄工时从 8-20 分钟压缩至 3-6 分钟
- **向 support（11.7%→目标 ≥20%）和 assassin（13.3%→目标 ≥18%）倾斜**——补齐现有角色配比短板
- **分批推进**：2-A（中国古典 85 英雄）→ 2-B（世界神话 40 英雄）→ 2-C（补充 35 英雄），每批独立 Gate C 验收

**预估总工期：12-22 人天（含审查），新增 ≥160 英雄，check_cards 绿，pytest 绿。**

---

## 1. 候选 IP 清单与英雄配额

### 1.1 入选原则

| 原则 | 说明 | 红线 |
|---|---|---|
| **公有领域** | 原著作者去世 >70 年（中国）/ >95 年（美国），或为口传神话无明确作者 | 一票否决 |
| **认知度** | 中文用户有基础认知，不需要额外教育成本 | 优先中国古典 |
| **角色多样性** | 至少覆盖 4/6 role，避免单一 role 堆积 | 最低要求 |
| **跨 IP 无英雄名重叠** | 同一英雄名不在两个公有领域 IP 中同时出现（如「哪吒」同时存在于西游记和封神演义） | 归入首次出现 IP |

### 1.2 候选 IP 总表

| # | IP | game_id | 英雄数 | 优先级 | 入选理由 |
|---|---|---|---|---|---|
| 1 | **三国演义** | `three_kingdoms` | 40 | P0 | 公有领域（罗贯中，约 1400 年）；中文用户认知第一；角色 120+ 取 40 精华 |
| 2 | **西游记** | `journey_to_the_west` | 25 | P0 | 公有领域（吴承恩，约 1580 年）；法术系角色天然丰富；跨 IP 角色（哪吒→归入封神） |
| 3 | **封神演义** | `fengshen_yanyi` | 20 | P0 | 公有领域（许仲琳，约 1567 年）；法术/法宝机制天然契合 D&D 豁免；哪吒/杨戬等招牌角色 |
| 4 | **北欧神话** | `norse_myth` | 20 | P1 | 公有领域（口传史诗，《埃达》约 13 世纪）；smite 有风格基线可参考；差异化 damage type（冰/雷/光） |
| 5 | **希腊神话** | `greek_myth` | 20 | P1 | 公有领域（口传神话）；资料最丰富；英雄/半神角色多样化 |
| 6 | **克苏鲁神话** | `cthulhu_mythos` | 15 | P2 | 公有领域（Lovecraft 1937 年去世，>70 年；部分早期作品版权争议已澄清）；WIS 豁免/心灵伤害差异化 |
| 7 | **世界历史名将** | `historical_generals` | 20 | P2 | 公有领域（历史人物不可版权化）；填补 fighter/marksman 缺口；跨文化 |

| **合计** | | | **160** | | 落入 GDD §2.4 的 120–200 区间中位 |

### 1.3 各 IP 具体英雄名单与暂定 Role

> **Role 分配遵循 GDD §2.4 约束：新增英雄中 support ≥20%（≥32 人）、assassin ≥18%（≥29 人）。**
> 以下为设计建议名单，最终名单由主理人审批确认。

#### 1.3.1 三国演义（`three_kingdoms`，40 人）

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 关羽 | fighter | STR 主，青龙偃月刀，挥砍伤害 |
| 2 | 张飞 | tank | STR+CON，丈八蛇矛，当阳桥喝断 |
| 3 | 赵云 | fighter | DEX+STR，长坂坡七进七出，accel |
| 4 | 马超 | fighter | DEX 主，西凉铁骑，穿刺伤害 |
| 5 | 黄忠 | marksman | DEX 主，百步穿杨，远程穿刺 |
| 6 | 诸葛亮 | mage | INT 主，八阵图/借东风，control+AOE |
| 7 | 刘备 | support | CHA 主，仁德，buff/heal |
| 8 | 曹操 | mage | INT+CHA，奸雄，control+sunder |
| 9 | 孙权 | support | CHA+WIS，制衡，buff/shield |
| 10 | 吕布 | assassin | STR+DEX，辕门射戟/无双，execute |
| 11 | 周瑜 | mage | INT 主，火烧赤壁，AOE+dot |
| 12 | 司马懿 | mage | INT+WIS，隐忍，control+reflect |
| 13 | 夏侯惇 | fighter | STR 主，拔矢啖睛，heal+execute |
| 14 | 夏侯渊 | marksman | DEX 主，神速，穿刺+accel |
| 15 | 典韦 | tank | CON 主，古之恶来，shield+reflect |
| 16 | 许褚 | tank | STR+CON，虎痴，reduce |
| 17 | 张辽 | fighter | STR+DEX，威震逍遥津，accel+sunder |
| 18 | 徐晃 | marksman | DEX 主，长驱直入，穿刺 |
| 19 | 甘宁 | assassin | DEX 主，锦帆贼，accel+execute |
| 20 | 太史慈 | fighter | STR+DEX，北海救孔融，accel |
| 21 | 孙策 | fighter | STR+DEX，小霸王，execute |
| 22 | 吕蒙 | assassin | DEX+INT，白衣渡江，invis+execute |
| 23 | 陆逊 | mage | INT 主，火烧连营，AOE+dot |
| 24 | 黄盖 | tank | STR+CON，苦肉计，reduce+shield |
| 25 | 鲁肃 | support | WIS+CHA，外交斡旋，buff/shield |
| 26 | 貂蝉 | assassin | CHA+DEX，连环计/离间，control+confuse |
| 27 | 魏延 | assassin | STR 主，子午谷奇谋，execute+accel |
| 28 | 庞统 | mage | INT+WIS，连环计，dot+control |
| 29 | 贾诩 | mage | INT+CHA，乱武/毒士，control+dot |
| 30 | 郭嘉 | mage | INT 主，十胜十败，buff+sunder |
| 31 | 荀彧 | support | WIS+INT，王佐之才，buff+heal |
| 32 | 曹仁 | tank | STR+CON，铁壁将军，shield+reduce |
| 33 | 颜良 | fighter | STR 主，河北猛将，挥砍 |
| 34 | 文丑 | fighter | STR 主，同颜良，挥砍 |
| 35 | 华雄 | fighter | STR 主，汜水关，execute |
| 36 | 董卓 | tank | CON+CHA，暴君，reduce+control |
| 37 | 孟获 | tank | STR+CON，南蛮王，reduce+shield |
| 38 | 祝融 | assassin | DEX 主，飞刀，dot+accel |
| 39 | 孙尚香 | marksman | DEX 主，弓腰姬，穿刺 |
| 40 | 华佗 | support | WIS 主，神医，heal+cleanse |

**三国 role 配比**：tank 5 / fighter 8 / assassin 8 / mage 8 / marksman 5 / support 6
→ support 15.0%、assassin 20.0%。Support 略低，需在下个 IP 补。

#### 1.3.2 西游记（`journey_to_the_west`，25 人）

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 孙悟空 | fighter | STR+DEX，金箍棒/七十二变，accel+execute |
| 2 | 猪八戒 | tank | STR+CON，九齿钉耙，shield+reduce |
| 3 | 沙悟净 | tank | STR+CON，降妖宝杖，shield |
| 4 | 唐僧 | support | WIS+CHA，紧箍咒/佛法，heal+control |
| 5 | 白龙马 | assassin | DEX 主，龙马化形，accel+invis |
| 6 | 牛魔王 | tank | STR+CON，混铁棍，reduce+sunder |
| 7 | 铁扇公主 | mage | INT 主，芭蕉扇，control+AOE（强风） |
| 8 | 红孩儿 | mage | INT 主，三昧真火，dot+AOE |
| 9 | 白骨精 | assassin | CHA+DEX，三变/魅惑，invis+control |
| 10 | 蜘蛛精 | assassin | DEX 主，蛛网/毒，slow+dot |
| 11 | 金角大王 | mage | INT 主，紫金红葫芦，control+execute |
| 12 | 银角大王 | mage | INT 主，羊脂玉净瓶，control+sunder |
| 13 | 六耳猕猴 | assassin | DEX+STR，与悟空同源，invis+accel |
| 14 | 二郎神 | fighter | STR+DEX，三尖两刃刀/天眼，execute+true_dmg |
| 15 | 观音菩萨 | support | WIS+CHA，净瓶/慈悲，heal+cleanse+shield |
| 16 | 如来佛祖 | mage | WIS+INT，五指山/佛法无边，control+AOE |
| 17 | 玉皇大帝 | support | CHA+WIS，天规/雷罚，buff+control |
| 18 | 太白金星 | support | CHA+WIS，调解/仙术，buff+heal |
| 19 | 黄袍怪 | fighter | STR 主，奎木狼星，挥砍+dot |
| 20 | 蝎子精 | assassin | DEX 主，倒马毒桩，dot+control |
| 21 | 大鹏金翅雕 | assassin | DEX 主，云程万里鹏，accel+execute |
| 22 | 青牛精 | tank | STR+CON，金刚琢，reduce+reflect |
| 23 | 九灵元圣 | mage | INT+WIS，九头狮，AOE+control |
| 24 | 金鼻白毛老鼠精 | assassin | DEX+CHA，地涌夫人，invis+dot |
| 25 | 嫦娥 | support | CHA+WIS，月宫仙子，buff+heal |

**西游 role 配比**：tank 4 / fighter 3 / assassin 7 / mage 6 / marksman 0 / support 5
→ support 20.0%、assassin 28.0%。marksman 严重不足，需在下个 IP 补。

#### 1.3.3 封神演义（`fengshen_yanyi`，20 人）

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 姜子牙 | support | WIS+INT，打神鞭/封神榜，buff+control |
| 2 | 哪吒 | fighter | STR+DEX，乾坤圈/风火轮/三头六臂，accel+AOE |
| 3 | 杨戬 | fighter | STR+WIS，三尖两刃刀/天眼/八九玄功，execute+true_dmg |
| 4 | 雷震子 | mage | INT+DEX，风雷双翼/黄金棍，AOE+accel |
| 5 | 妲己 | assassin | CHA+DEX，狐妖/魅惑，control+confuse |
| 6 | 纣王 | tank | STR+CON，暴君，reduce+sunder |
| 7 | 申公豹 | mage | INT+CHA，飞头术/阐教叛徒，control+dot |
| 8 | 闻仲 | fighter | STR+INT，雌雄双鞭/墨麒麟，execute+control |
| 9 | 黄飞虎 | fighter | STR+DEX，五色神牛，accel+sunder |
| 10 | 土行孙 | assassin | DEX 主，地行术/捆仙绳，invis+control |
| 11 | 邓婵玉 | marksman | DEX 主，五色石投掷，穿刺+slow |
| 12 | 龙吉公主 | mage | INT+CHA，水系法术/神龙，control+AOE |
| 13 | 赵公明 | mage | INT+WIS，定海珠/缚龙索，control+true_dmg |
| 14 | 云霄娘娘 | mage | INT+WIS，混元金斗/九曲黄河阵，AOE+control |
| 15 | 孔宣 | fighter | STR+WIS，五色神光（收万物），reflect+sunder |
| 16 | 袁洪 | assassin | STR+DEX，白猿/八九玄功，accel+execute |
| 17 | 比干 | support | WIS 主，七窍玲珑心，heal+buff |
| 18 | 魔礼青 | fighter | STR 主，青云剑，挥砍+control |
| 19 | 张桂芳 | assassin | CHA+WIS，呼名落马术，control+execute |
| 20 | 金灵圣母 | support | WIS+INT，万仙阵主，buff+shield+cleanse |

**封神 role 配比**：tank 1 / fighter 5 / assassin 4 / mage 5 / marksman 1 / support 4
→ support 20.0%、assassin 20.0%。tank 和 marksman 偏少，属 IP 特色（法术法宝为主）。

#### 1.3.4 北欧神话（`norse_myth`，20 人）

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 奥丁 | mage | WIS+INT，智慧之泉/冈格尼尔之枪，control+true_dmg |
| 2 | 索尔 | fighter | STR+CON，雷神之锤，AOE+control（雷击） |
| 3 | 洛基 | assassin | CHA+DEX，诡计之神，invis+control+confuse |
| 4 | 芙蕾雅 | support | CHA+WIS，爱与美/魔法，buff+heal+shield |
| 5 | 海姆达尔 | marksman | WIS+DEX，彩虹桥守护者/全视之眼，穿刺+true_dmg |
| 6 | 提尔 | fighter | STR 主，战神/断臂，execute+sunder |
| 7 | 巴德尔 | support | WIS+CHA，光明之神/不可伤害，shield+heal |
| 8 | 弗雷 | fighter | STR+WIS，胜利之剑，accel+buff |
| 9 | 斯卡蒂 | marksman | DEX 主，冬之女神/狩猎，穿刺+slow |
| 10 | 赫尔 | mage | INT+WIS，冥界女王，control+dot |
| 11 | 芬里尔 | assassin | STR+DEX，噬神巨狼，execute+accel |
| 12 | 耶梦加得 | tank | CON+STR，尘世巨蟒，reduce+dot |
| 13 | 布伦希尔德 | support | WIS+STR，女武神，buff+shield+heal |
| 14 | 希芙 | support | CHA+WIS，丰收女神，heal+buff |
| 15 | 密米尔 | mage | INT+WIS，智慧之头，buff+sunder |
| 16 | 尼德霍格 | assassin | STR+CON，啃食世界树的黑龙，dot+execute |
| 17 | 苏尔特尔 | tank | STR+INT，火焰巨人/暮光之剑，AOE+dot |
| 18 | 弗雷雅 | mage | INT+CHA，魔法女神，AOE+control |
| 19 | 霍德尔 | assassin | DEX 主，盲神/槲寄生之箭，execute+invis |
| 20 | 乌勒尔 | marksman | DEX 主，狩猎之神，穿刺+slow |

**北欧 role 配比**：tank 2 / fighter 4 / assassin 5 / mage 5 / marksman 3 / support 1
→ support 5.0%（严重不足！需在希腊神话补）。

> ⚠️ 北欧神话的 healing/support 角色较少，是 IP 天然特征。缺口由希腊神话与历史名将补足。

#### 1.3.5 希腊神话（`greek_myth`，20 人）

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 宙斯 | mage | INT+WIS，雷霆之主，AOE+control |
| 2 | 赫拉 | support | CHA+WIS，天后/婚姻守护，buff+shield+control |
| 3 | 波塞冬 | mage | INT+STR，海神/三叉戟，AOE+control |
| 4 | 哈迪斯 | tank | CON+WIS，冥王/隐身头盔，reduce+invis |
| 5 | 雅典娜 | support | WIS+INT，智慧/战争女神，buff+shield+cleanse |
| 6 | 阿波罗 | marksman | DEX+CHA，太阳神/弓箭/音乐，穿刺+heal |
| 7 | 阿瑞斯 | fighter | STR+CON，战神，execute+sunder |
| 8 | 赫菲斯托斯 | support | STR+INT，火神/工匠，buff+shield |
| 9 | 赫尔墨斯 | assassin | DEX+CHA，神使/速度/盗窃，accel+invis |
| 10 | 阿佛洛狄忒 | support | CHA+WIS，爱与美，heal+buff+control |
| 11 | 阿耳忒弥斯 | marksman | DEX+WIS，狩猎女神/月神，穿刺+accel |
| 12 | 珀耳塞福涅 | mage | CHA+INT，冥后/春之女神，control+dot |
| 13 | 赫拉克勒斯 | fighter | STR+CON，大力神/十二试炼，execute+reduce |
| 14 | 阿喀琉斯 | fighter | STR+DEX，半神战士/脚踝弱点，execute+accel |
| 15 | 珀尔修斯 | assassin | DEX+STR，斩美杜莎/飞天鞋，execute+accel |
| 16 | 美杜莎 | assassin | CHA+WIS，蛇发/石化凝视，control+execute |
| 17 | 喀戎 | support | WIS+DEX，半人马贤者/导师，heal+buff |
| 18 | 潘多拉 | mage | CHA+WIS，灾难魔盒，AOE+dot+debuff |
| 19 | 厄里倪厄斯 | assassin | WIS 主，复仇三女神，dot+control |
| 20 | 得墨忒耳 | support | WIS+CHA，丰收/大地，heal+buff |

**希腊 role 配比**：tank 1 / fighter 3 / assassin 4 / mage 5 / marksman 2 / support 5
→ support 25.0%、assassin 20.0%。补回北欧缺口。

#### 1.3.6 克苏鲁神话（`cthulhu_mythos`，15 人）

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 克苏鲁 | mage | WIS+CON，拉莱耶之主/星之眷族，control+AOE（心灵） |
| 2 | 奈亚拉托提普 | assassin | CHA+DEX，千面之神/混沌，invis+confuse+control |
| 3 | 莎布·尼古拉丝 | support | CON+WIS，孕育万千子孙的森之黑山羊，heal+buff |
| 4 | 犹格·索托斯 | mage | INT+WIS，全知/时空之门，AOE+control |
| 5 | 哈斯塔 | mage | INT+CHA，黄衣之王/卡尔克萨，dot+control |
| 6 | 达贡 | tank | STR+CON，深海之主，reduce+shield |
| 7 | 深潜者 | fighter | STR+CON，鱼人战士，execute+accel |
| 8 | 修格斯 | tank | CON+STR，无定形原生质，reduce+reflect |
| 9 | 阿撒托斯 | mage | WIS+INT，盲目痴愚之核/宇宙中心，AOE+control+true_dmg |
| 10 | 兰道夫·卡特 | support | WIS+INT，梦境穿越者，buff+heal |
| 11 | 古老者 | mage | INT+WIS，南极远古文明，AOE+slow |
| 12 | 米·戈 | assassin | INT+DEX，犹格斯星真菌，dot+sunder |
| 13 | 诺登斯 | support | WIS 主，幻梦境主神，shield+cleanse+heal |
| 14 | 夜魇 | assassin | DEX+WIS，无面黑暗，invis+dot+execute |
| 15 | 蛇人 | assassin | DEX+CHA，地下文明，invis+dot |

**克苏鲁 role 配比**：tank 2 / fighter 1 / assassin 4 / mage 5 / marksman 0 / support 3
→ support 20.0%、assassin 26.7%。marksman 为 0——非人形生物天然不适合射手定位，可接受。

#### 1.3.7 世界历史名将（`historical_generals`，20 人）

> ⚠️ 已回避与三国的重复（如吕布、关羽等），优先选不同时代/地域的代表。

| # | 英雄 | 暂定 Role | 设计锚点 |
|---|---|---|---|
| 1 | 项羽 | fighter | STR+CON，力拔山兮/霸王枪，execute+sunder |
| 2 | 成吉思汗 | marksman | DEX+WIS，蒙古铁骑/骑射，穿刺+accel |
| 3 | 拿破仑 | support | CHA+INT，炮兵/战略，buff+sunder |
| 4 | 亚历山大 | fighter | STR+CHA，马其顿方阵，accel+execute |
| 5 | 凯撒 | support | CHA+INT，罗马军团/战策，buff+shield |
| 6 | 汉尼拔 | assassin | INT+DEX，翻越阿尔卑斯/战象奇袭，execute+control |
| 7 | 岳飞 | fighter | STR+WIS，精忠报国/岳家枪，execute+sunder |
| 8 | 戚继光 | support | WIS+INT，鸳鸯阵/抗倭，buff+shield |
| 9 | 韩信 | assassin | INT+DEX，暗度陈仓/背水一战，accel+execute |
| 10 | 白起 | assassin | STR+INT，人屠/长平之战，execute+AOE |
| 11 | 李广 | marksman | DEX 主，飞将军/骑射，穿刺+slow |
| 12 | 霍去病 | assassin | DEX+STR，封狼居胥/长途奔袭，accel+execute |
| 13 | 李靖 | support | INT+WIS，大唐军神/兵法，buff+control |
| 14 | 薛仁贵 | marksman | DEX+STR，三箭定天山，穿刺+execute |
| 15 | 帖木儿 | fighter | STR+INT，跛子征服者，sunder+execute |
| 16 | 织田信长 | assassin | CHA+INT，第六天魔王/铁炮三段，execute+AOE |
| 17 | 圣女贞德 | support | CHA+WIS，奥尔良少女/圣旗，heal+buff+shield |
| 18 | 萨拉丁 | tank | STR+WIS+CHA，圣城守护者，shield+reduce |
| 19 | 列奥尼达 | tank | STR+CON，斯巴达三百勇士，shield+reduce |
| 20 | 卑弥呼 | support | WIS+CHA，邪马台女王/鬼道，buff+heal |

**历史名将 role 配比**：tank 2 / fighter 3 / assassin 5 / mage 0 / marksman 3 / support 7
→ support 35.0%、assassin 25.0%。mage 为 0——历史名将天然不适合法师定位（除非把「军师/谋士」归入 mage，但这与三国角色定位冲突）。

### 1.4 全局 Role 配比汇总与验证

#### 1.4.1 新增 IP 内部配比

| Role | 三国 | 西游 | 封神 | 北欧 | 希腊 | 克苏鲁 | 历史 | **合计** | **占比** |
|---|---|---|---|---|---|---|---|---|---|
| tank | 5 | 4 | 1 | 2 | 1 | 2 | 2 | **17** | 10.6% |
| fighter | 8 | 3 | 5 | 4 | 3 | 1 | 3 | **27** | 16.9% |
| assassin | 8 | 7 | 4 | 5 | 4 | 4 | 5 | **37** | **23.1%** ✅ |
| mage | 8 | 6 | 5 | 5 | 5 | 5 | 0 | **34** | 21.3% |
| marksman | 5 | 0 | 1 | 3 | 2 | 0 | 3 | **14** | 8.8% |
| support | 6 | 5 | 4 | 1 | 5 | 3 | 7 | **31** | **19.4%** ⚠️ |
| **合计** | 40 | 25 | 20 | 20 | 20 | 15 | 20 | **160** | |

> ⚠️ support 19.4% 离目标的 ≥20% 差 0.6pp（差 1 人）。建议在最终 Role 调优时将 1 名 mage 或 fighter 转为 support。

#### 1.4.2 合入后全池配比预测

| Role | 现有 | 新增 | 合入后 | 占比 | 变化 |
|---|---|---|---|---|---|
| tank | 260 | 17 | 277 | 15.2% | -0.5pp |
| fighter | 367 | 27 | 394 | 21.7% | -0.5pp |
| **assassin** | 220 | 37 | 257 | **14.1%** | **+0.8pp** ↑ |
| mage | 372 | 34 | 406 | 22.3% | -0.1pp |
| marksman | 246 | 14 | 260 | 14.3% | -0.5pp |
| **support** | 194 | 31 | 225 | **12.4%** | **+0.7pp** ↑ |
| **合计** | 1659 | 160 | 1819 | | |

> 结论：新增 160 英雄后，support 从 11.7% → 12.4%（+0.7pp），assassin 从 13.3% → 14.1%（+0.8pp）。改善幅度温和但方向正确。若要加速收敛，后续 Wave 3 可加大 support/assassin 比重。

---

## 2. 新增 IP 操作步骤清单

> 基于 `docs/architecture/content-pipeline-readiness.md` §3.3 与 ADR-005 实施后的最新管线状态。

### 2.1 单 IP 标准化 7 步流程

以新增 `three_kingdoms` 为例：

#### 步骤 1：注册 game_id 到 Registry

**文件**：`core/registry.py:28-53`

```python
# 在 GAME_REGISTRY 字典末尾新增条目
"three_kingdoms": {"display": "Romance of the Three Kingdoms", "cn": "三国演义", "hero_file": "heroes.json"},
```

**验证**：`python -c "from core.registry import GAME_NAME_CN; print(GAME_NAME_CN.get('Romance of the Three Kingdoms'))"` → 应输出 `三国演义`

> ⚠️ game_id 必须是 `小写 snake_case`，与目录名/技能文件名完全对齐。`_slugify` 已在 ADR-005 C-6 修复为小写。

#### 步骤 2：建 `data/source/<game_id>/` 源数据文件

```bash
mkdir data/source/three_kingdoms
```

**文件**：`data/source/three_kingdoms/heroes.json`

格式参考现有 `data/source/league_of_legends/` 的 `champions.json`。最小条目：

```json
[
  { "name": "关羽", "game": "Romance of the Three Kingdoms" },
  { "name": "张飞", "game": "Romance of the Three Kingdoms" }
]
```

**文件**：`data/source/three_kingdoms/ATTRIBUTION.md`

内容模板参考 §3.3。

#### 步骤 3：建 `data/skills/<game_id>/` 技能数据（每英雄一个文件）

```bash
# 为每英雄新建一个文件，内容为 4 技能 dict 的 list
mkdir -p data/skills/three_kingdoms
echo '[]' > data/skills/three_kingdoms/示例英雄.json
```

然后按 Wave 1 附录 A 格式填入英雄→技能映射。最低要求：前 5 个英雄完成即可跑通管线验证。

**自动化工具**：可用 `card_tool.py add-game` 子命令完成步骤 2+3 的骨架创建（`card_tool.py:530-594`）。但当前 `add-game` 使用 `input()` 交互——ADR-005 C-13 已建议改为 CLI 参数，若尚未实施则手动创建。

#### 步骤 4：生成角色卡 + 验证

```bash
# 生成
python tools/card_tool.py generate --game three_kingdoms

# 验证
python tools/card_tool.py validate
python tools/check_cards.py
```

#### 步骤 5：重建索引 + 更新状态

```bash
python tools/card_tool.py status
```

`card_tool.py` 的 `rebuild_index`（如果存在）会自动更新 `data/character_cards/_index.json`。

#### 步骤 6：全链路验证

```bash
# 启动 UI 确认新 IP 英雄可被加载
python main.py

# 跑战斗模拟验证
python -m pytest tests/ -v
```

#### 步骤 7：Gate C 验收（见 §5.2）

### 2.2 批量 IP 并行策略

```
批次 2-A（中国古典 85 英雄）：
  three_kingdoms (40) ─┬─ 步骤1-2 并行 ─→ 步骤3-4 串行 ─→ 步骤5-7
  journey_to_the_west (25) ─┤
  fengshen_yanyi (20) ─────┘

批次 2-B（世界神话 40 英雄）：
  norse_myth (20) ─┬─ 同上
  greek_myth (20) ─┘

批次 2-C（补充 35 英雄）：
  cthulhu_mythos (15) ─┬─ 同上
  historical_generals (20) ─┘
```

**理由**：步骤 1-2（建目录、注册、写 hero 名单）可并行；步骤 3-4（技能映射、生成、验证）需串行以确保每 IP 质量。

---

## 3. 技能数据生成策略

### 3.1 公有领域技能来源 → D&D 映射路径

与 Wave 1（爬取 wiki → D&D 映射 → 审查）不同，Wave 2 的技能来源是**文献描述与演义叙述**，需经过一道「文本→机制」翻译。

| IP | 技能来源 | 映射策略 | D&D 化难度 |
|---|---|---|---|
| 三国演义 | 《三国演义》原著战斗场景、民间武评/兵器文化、成语典故 | **兵器→damage_type、战术典故→effect** | ⭐ 低 |
| 西游记 | 《西游记》原著法术描述、法宝功能 | **法宝=控制/豁免、筋斗云/变化=accel** | ⭐⭐ 中 |
| 封神演义 | 《封神演义》原著法术/法宝/阵法 | **法宝=saving_throw核心、阵法=AOE** | ⭐⭐ 中 |
| 北欧/希腊神话 | 《埃达》《伊利亚特》《奥德赛》等史诗 | **神职=primary_attr、神器=signature skill** | ⭐ 低 |
| 克苏鲁神话 | Lovecraft 原著小说中的非凡实体描述 | **SAN值→WIS豁免、触手/疯狂=control** | ⭐⭐⭐ 高 |
| 世界历史名将 | 正史/兵书记载的战绩与兵种 | **战术=effect、兵种=damage_type&range** | ⭐ 低 |

**核心原则（Gate E-6）**：技能机制必须是**D&D 5e 再诠释**，而非搬运任何商业游戏的数值。对公有领域 IP，这一点天然成立——罗贯中不会写 `1d8+STR 挥砍伤害`。

### 3.2 复用 role_dnd_templates.json 加速

`tools/_archive/role_dnd_templates.json` 包含 6 role × QWER 四槽的完整 D&D 模板，含：
- 骰型组合（已落入 GDD §3.2 配额带 24–34）
- CD 默认值（`[0, 1, 2, 4]`，通过 G-2 护栏）
- effects 候选池（每 role 2-5 类，已命中 `mechanics.py` 别名表）
- saving_throw 惯例（dc_formula、豁免属性）

**复用策略**：

```
Step 1: 确定英雄 Role → 直接套用对应 role 模板的 dice/attr/range/cd
Step 2: 为 1-2 个「招牌技能」定制 effect（基于原著描述）
Step 3: 校验 E 落入配额带 + effects 命中别名表 + CD 合规
Step 4: 描述用 D&D 风味改写
```

**效率估算**：

| 方式 | 每英雄工时 | 说明 |
|---|---|---|
| 纯手工（Wave 1 Phase 2 基线） | 8-20 分钟 | 从零设计每个技能的 dice/effects/saving_throw |
| **模板复用（Wave 2）** | **3-6 分钟** | 模板提供 80% 框架，只需定制 1-2 个 signature effect |
| **效率提升** | **65-75%** | 对 fighter/tank/marksman 提升最大（技能结构相对标准化） |

**各 IP 模板适用性**：

| IP | 模板适用度 | 说明 |
|---|---|---|
| 三国演义 | ★★★★★ | 武将→fighter/tank/marksman 完美匹配；谋士→mage |
| 西游记 | ★★★★ | 妖怪→fighter/assassin 匹配；法宝型角色需更多定制 |
| 封神演义 | ★★★ | 法宝系统在模板中无直接对应，R 槽需定制 saving_throw |
| 北欧神话 | ★★★★ | 神祇→按神职对应 role，模板匹配度高 |
| 希腊神话 | ★★★★ | 同上 |
| 克苏鲁神话 | ★★ | 心灵/疯狂机制模板未覆盖，需定制 effect 别名扩展 |
| 世界历史名将 | ★★★★★ | 武将→fighter/tank/marksman 完美匹配；战略家→support |

### 3.3 ATTRIBUTION.md 模板（公有领域版）

新增 IP 的 `data/source/<game_id>/ATTRIBUTION.md` 使用以下模板（与商业 IP 版区分）：

```markdown
# ATTRIBUTION — [IP 中文名]（[英文名]）

## 公有领域声明

本目录下的角色数据来源于 **[原著名称]**，该书成书于 **[年代]**，
作者 **[作者名]** 去世已超过 70 年，在主要司法管辖区已进入**公有领域**。

## 数据转化

本项目中存储的角色技能数据已通过 **D&D 5e 数值框架** 进行再诠释和数值映射。
技能名称为对原著角色的标识性引用，技能机制为基于原著描述的原创游戏设计，
不构成对任何第三方游戏、影视或文学改编作品的侵权。

## 免责

本项目为 **非商业性的粉丝项目**。任何第三方若认为特定内容构成侵权，
请联系项目维护者：[待补充]
```

### 3.4 跨 IP 英雄名冲突处理

以下英雄名在多个 IP 中出现，按「首次出现的 IP 持有、其他 IP 跳过」原则处理：

| 英雄名 | 出现 IP | 决策 | card_id |
|---|---|---|---|
| 哪吒 | 封神演义（首次）、西游记 | **仅出现在封神演义**；西游英雄列表已排除 | `fengshen_yanyi:哪吒` |
| 二郎神/杨戬 | 封神演义（首次）、西游记 | **仅出现在封神演义**；西游保留二郎神但以"杨戬"为主名 | `fengshen_yanyi:杨戬` |
| 宙斯 | smite（已存在）、greek_myth | 两者保留，card_id 前缀不同：`smite:宙斯` vs `greek_myth:宙斯` | 不冲突 |
| 吕布 | three_kingdoms、historical_generals | **仅出现在三国演义**；历史名将列表已排除 | `three_kingdoms:吕布` |

> loader 的 `build_hero_dict` 已有碰撞检测（ADR-005 C-3），即使出现同名也会自动消歧并告警，不会静默丢卡。

---

## 4. 与现有系统的对齐

### 4.1 card_tool status 更新

`tools/card_tool.py:226` 仍硬编码 `{len(detailed)}/16`（评估报告 N-3）。Wave 2 新增 7 IP 后需修复为动态分母。

**改动**：

```python
# 修改前（:226）
print(f"\n  技能文件覆盖: {len(detailed)}/16 详细, {len(placeholder)}/16 占位...")

# 修改后
total_games = len(REGISTRY_BY_ID)
print(f"\n  技能文件覆盖: {len(detailed)}/{total_games} 详细, {len(placeholder)}/{total_games} 占位...")
```

**影响**：仅 cosmetic，不影响功能。建议在第一批新 IP 合入时顺手修。

### 4.2 check_cards 适配

`tools/check_cards.py` 已在 ADR-005 实施后使用 `iter_card_files` 统一扫描（`:21 import iter_card_files`），**无需对 `data/source/` 新格式做适配**。

当前 check_cards 逻辑：
1. 遍历 `data/character_cards/**/*.json` → **自动覆盖新 IP**
2. 检查 `skills: dict` 残留 → 模板复用产出的 `list[Skill]` 不会触发
3. 检查 schema 契约 → 模板已验证合规
4. 检查 card_id 唯一性（ADR-005 C-5）→ `<game_id>:<hero_name>` 天然唯一

**结论：对新 IP 零适配，直接可用。**

### 4.3 loader `_index.json` 更新

`data/character_cards/_index.json` 由 `card_tool.py` 的 `rebuild_index` 写入，**不参与运行时加载**（loader 走 `iter_card_files` 递归扫描）。

- `generate --game <IP>` 后自动更新（如果 generate 内部调用了 rebuild_index）
- 如果 generate 未触发，手动跑 `python tools/card_tool.py rebuild_index`
- 对于 Wave 2 而言，`_index.json` 是**信息展示**用途，不影响功能

### 4.4 pytest 测试套件对齐

现有测试（`tests/test_loader.py`、`test_schema.py`、`test_battle_smoke.py` 等）基于**全库扫描**，新增 IP 自动纳入测试范围：

- `test_loader.py` → 验证新 IP 卡片可被加载、碰撞检测生效
- `test_schema.py` → 验证新卡片通过契约
- `test_battle_smoke.py` → 新增英雄进入随机对战池

**唯一需要新增的测试**（建议交程基岩）：

```python
# tests/test_wave2.py
def test_all_new_ips_have_skills_file():
    """验证 WAVE2_IPS 中每个 IP 都有 data/skills/<game_id>/ 目录且每英雄一个技能文件"""
    ...

def test_new_heroes_pass_gate_c():
    """验证新增英雄的骰期望、CD、effects 合规"""
    ...

def test_no_duplicate_hero_names_across_new_ips():
    """验证跨公有领域 IP 无明显英雄名重叠"""
    ...
```

### 4.5 现有 balance.py 常量

**GDD §3.1 护栏全部维持不变**：`DAMAGE_SCALE=0.35`、`HP_SCALE=10`、引擎 4 槽、默认 CD、等级缩放——一律冻结。新增英雄的强度边界由**骰期望配额带（24-34）**和**CD 护栏（avg≤3.0, s0=0）**控制，不调全局旋钮。

---

## 5. 工期估算与验收标准

### 5.1 工时估算

| 阶段 | 任务 | 每 IP 工时 | IP 数 | 小计 | 说明 |
|---|---|---|---|---|---|
| **2-A** | 三国演义（40 英雄） | 3.0 人天 | 1 | 3.0 | 40 英雄 × 4.5 分钟 = 3 小时；+1 小时审查 |
| | 西游记（25 英雄） | 2.0 人天 | 1 | 2.0 | 25 英雄 × 4.8 分钟；法宝型定制稍慢 |
| | 封神演义（20 英雄） | 1.8 人天 | 1 | 1.8 | 20 英雄 × 5.4 分钟；法宝定制最多 |
| | 2-A 审查 + Gate C | 0.5 人天 | — | 0.5 | 抽检 10% + 对战仿真 |
| | **2-A 小计** | | | **7.3 人天** | |
| **2-B** | 北欧神话（20 英雄） | 1.3 人天 | 1 | 1.3 | 20 英雄 × 4 分钟 |
| | 希腊神话（20 英雄） | 1.3 人天 | 1 | 1.3 | 同上 |
| | 2-B 审查 + Gate C | 0.5 人天 | — | 0.5 | |
| | **2-B 小计** | | | **3.1 人天** | |
| **2-C** | 克苏鲁神话（15 英雄） | 1.5 人天 | 1 | 1.5 | 定制度最高（心灵/疯狂新 effect 可能需别名扩展） |
| | 世界历史名将（20 英雄） | 1.3 人天 | 1 | 1.3 | |
| | 2-C 审查 + Gate C | 0.5 人天 | — | 0.5 | |
| | **2-C 小计** | | | **3.3 人天** | |
| **前置** | registry 注册 + ATTRIBUTION 创建 | 0.1 人天 | 7 | 0.7 | 模板化，批量完成 |
| **收尾** | card_tool status 硬编码修复 + pytest 新增测试 | 0.5 人天 | — | 0.5 | 交程基岩 |
| **汇总** | | | | **~15 人天** | 下限 12 人天（顺利），上限 22 人天（审查退回/效果扩展） |

> **基准校准**：Wave 1 的 LoL 172 英雄纯人工（8-20 分钟/英雄）= 4 人天。Wave 2 的 160 英雄有模板复用（3-6 分钟/英雄），理论上 2-3 倍效率提升 → **总工时 12-22 人天**，中位 15 人天。

### 5.2 每批 Gate C 验收标准

每批合入前，严守真（测试）执行以下验收（全自动，seed 固定）：

| ID | 判据 | 阈值 | 备注 |
|---|---|---|---|
| C-2 | 全池胜率 σ | **≤ 当前 σ + 2pp**（允许 ±2pp 波动） | σ~26pp 为真英雄天然强度差异的结构性天花板，不要求继续下降 |
| C-5 | 极值英雄（<25% 或 >75%） | **数量不增加** | 新增英雄不应引入新的极端值 |
| C-6 | 新增 IP vs 存量随机的对位胜率 | **落入 42%–58%** | 略宽于存量标准（45-55%），因新 IP 英雄规模小、统计噪声大 |
| C-13 | 新增英雄骰期望 E 落入配额带（24–34） | **≥ 95%** | 硬门 |
| C-14 | CD 合规（avg≤3.0, s0=0） | **100%** | 硬门 |
| D-1 | 存量英雄胜率漂移 | 单英雄 **Δ ≤ 5pp** | 防新增打崩存量 |
| D-4 | pytest 套件 | **全绿** | |
| E-1 | 技能描述与任何商业游戏 wiki 相似度 | 不适用（公有领域来源） | 改为：技能描述与原著直接引用 **< 30 字连续相同** |
| E-5 | 新增 IP 100% 公有领域 | **人工确认** | 主理人审批 |

**放宽说明**：σ 允许轻微波动（±2pp），因为：
1. 28pp（当前 σ 约数）是真技能英雄间的天然强度差异，是结构性的（有 saving_throw 的英雄天然强于没有的）
2. Wave 2 的新英雄全部是**真技能**（模板+定制），不会引入 T3 残卡或 T4 模板卡
3. 但 160 个新英雄加入全池会轻微改变匹配分布，±2pp 在正常统计噪声范围内

### 5.3 Wave 2 完成定义（Definition of Done）

| 指标 | 阈值 | 验证方式 |
|---|---|---|
| 新增英雄数 | **≥ 160** | `card_tool.py status` |
| 新增 IP 数 | **7** | 同上 |
| Gate C 全部通过 | **PASS** | 严守真报告 |
| `check_cards.py` | **退出码 0，零 errors** | CI |
| `pytest` | **全绿** | CI |
| ATTRIBUTION.md | **7 个新 IP 全部齐备** | 文件存在性检查 |
| 公有领域合规 | **100%（无新增商业 IP）** | 人工审批 |
| card_id 唯一性 | **零碰撞** | check_cards.py card_id 去重断言 |

---

## 6. 风险管理

### R-1 英雄名商标风险 —— **低（已缓解）**

| 项 | 内容 |
|---|---|
| **描述** | 公有领域角色的名字（如"关羽""孙悟空"）是否可能被商业游戏公司注册为商标？ |
| **分析** | ① 中国《商标法》第十条/十一条：历史人名、文学作品中的虚拟角色名**缺乏固有显著性**，难以单独注册为商标；② 即使有商标注册（如某公司的"王者荣耀×孙悟空"联名商标），**保护的是具体商业使用场景下的标识**，不是角色名本身；③ 本项目使用纯文字名作为 card_id 和显示名，**不涉及任何视觉设计、Logo 或商业推广**，不构成商标使用；④ 最坏情况：收到通知后移除特定英雄——目录隔离已是天然支持（删一个 JSON 文件即可）。 |
| **缓解** | ① ATTRIBUTION.md 明确声明公有领域来源；② 所有英雄使用原著原名，不加商业修饰前缀；③ 建立"单英雄快速摘除"能力（已有目录隔离天然支持） |
| **残余风险** | **极低**——至今无任何公有领域角色名因在粉丝项目中使用而被主张商标权的公开案例 |

### R-2 游戏机制过于接近某款商业游戏 —— **低**

| 项 | 内容 |
|---|---|
| **描述** | 三国英雄的 D&D 化技能若与某款商业 MOBA（如《王者荣耀》《三国杀》《真三国无双》）的技能效果过于相似，可能引发抄袭指控 |
| **分析** | ① D&D 5e SRD 是公开游戏规则（OGL/CC），将三国角色映射到 `1d8+STR`、`DEX 豁免半伤` 等泛用规则，**不受版权保护**（游戏规则不享有版权）；② `effects` 词表（如 control/slow/heal/shield）是通用游戏机制词汇；③ 本项目**没有经济系统（装备/符文）、没有小兵/防御塔、没有 5v5 地图**，产品形态（1v1 回合制卡牌战斗）与任何商业 MOBA 完全不同，不存在市场混淆风险；④ 技能名使用成语/典故（如"温酒斩华雄"被 D&D 化为"1d10+STR 挥砍伤害，execute 效果"），不是搬运任何特定游戏的技能名 |
| **缓解** | ① 技能描述一律用 D&D 风味改写，不用任何商业游戏技能名（如不用"破军"而写"力破千军，2d8+STR"）；② Gate E-6 确保机制是 D&D 再诠释 |
| **残余风险** | **极低** |

### R-3 克苏鲁神话版权边界 —— **低**

| 项 | 内容 |
|---|---|
| **描述** | Lovecraft 部分晚期作品（1924-1937）的版权状态曾存在争议。部分"克苏鲁神话"元素由 August Derleth 等后继作者创建，其版权状态各异 |
| **缓解** | ① 只使用 Lovecraft 本人的早期核心实体（克苏鲁、奈亚拉托提普、阿撒托斯等）——这些在 1920s 发表的实体已确认在美国和中国进入公有领域（作者 1937 年去世 + 70 年 = 2007 年过期）；② 不使用 Derleth 或 Chaosium 公司特有的"克苏鲁神话"体系术语；③ 技能描述基于 Lovecraft 原文的 D&D 化再诠释 |
| **残余风险** | **低**——建议在 ATTRIBUTION.md 中特别注明只使用 Lovecraft 本人的早期作品实体 |

### R-4 σ 恶化风险 —— **中**

| 项 | 内容 |
|---|---|
| **描述** | 新增 160 名英雄使用统一模板+定制，可能产生新的强度模式。如果定制 effects 的分布不均匀（例如某个 IP 的 mage 普遍偏强），可能抬高全池 σ |
| **早期信号** | 2-A 验收时 C-2 σ 上升 > 2pp；新增 IP 内胜率方差 > 存量平均 |
| **缓解** | ① 分批推进——2-A 先合入后观察 σ 变化再决定 2-B 是否调整策略；② 每批 Gate C 采样协议覆盖新增 IP vs 存量对照；③ 如果某 IP 系统性偏强，排查是否 effects 定制过于激进（降低 dice_count 或增加 CD 即可收敛） |
| **残余风险** | **低**——模板的骰期望和 CD 已校准到配额带内，定制只影响 effects 多样性，不大规模影响数值强度 |

### R-5 模板同质化风险 —— **中**

| 项 | 内容 |
|---|---|
| **描述** | 如果过度依赖模板（只改名字不改 effects），每个 IP 内部不同英雄会感觉"换皮"——与 Wave 1 之前的 T4 模板卡问题同质 |
| **早期信号** | 同一 IP 内 effects 类别熵 < 4（即全 IP 只用 4 类 effect） |
| **缓解** | ① 每个英雄的 1-2 个 signature skill **必须定制 effect**（不可全用模板默认）；② 每批抽检 10% 审查"机制辨识度"；③ 同为三国 fighter——关羽侧重 execute、赵云侧重 accel、马超侧重 sunder、张飞侧重 control——即使骰面相似，战斗体感不同 |
| **残余风险** | **低** |

### R-6 管线容量风险 —— **低**

| 项 | 内容 |
|---|---|
| **描述** | 1659 + 160 = 1819 张卡。loader 实测 0.67 ms/卡 × 1819 ≈ 1.2 秒，仍在 < 2s 的可接受范围内。但 card_tool status 报告和 _index.json 需更新。 |
| **缓解** | 已在 §4.1-4.3 列出需要更新的点 |
| **残余风险** | **极低** |

### R-7 跨 IP 神话角色重名 —— **低**

| 项 | 内容 |
|---|---|
| **描述** | 希腊神话的"宙斯"已存在于 smite（`smite:宙斯`），新增 `greek_myth:宙斯` 会在对战池中出现两个"宙斯" |
| **缓解** | card_id 前缀天然区分（`smite:宙斯` vs `greek_myth:宙斯`）；UI 显示名会带游戏名（`[神之浩劫] 宙斯` vs `[希腊神话] 宙斯`）；`build_hero_dict` 碰撞检测会处理任何意外 |
| **残余风险** | **极低**——这是设计预期行为，两个"宙斯"是不同游戏的 D&D 化诠释 |

---

## 7. 待主理人 / 用户拍板

| # | 决策点 | 选项 | 建议 |
|---|---|---|---|
| Q1 | Wave 2 候选 IP 是否全部通过？ | 7 个全做 / 减法（如砍克苏鲁或历史名将） | **7 个全做**——160 英雄是形成"新阵营"体感的最小量 |
| Q2 | 每 IP 英雄配额是否认可？ | 按 §1.2 表 / 调整某 IP 数量 | 建议认可；若觉得克苏鲁 15 偏多可减至 10（总量 155） |
| Q3 | 英雄名名单是否需要逐人审批？ | 是 / 按分组成批审批 / 不做逐人审批 | **分组成批审批**（中国古典一捆、世界神话一捆、其他一捆）|
| Q4 | Role 具体分配是我定还是给你框架你填充？ | 文策渊全定 / 主理人逐人指定 | **文策渊按模板初填，主理人抽检重点角色** |
| Q5 | 模板复用策略是否认可？ | 复用 / 纯手工 | **复用**——否则工时翻 3 倍 |
| Q6 | 克苏鲁是否引入新的 effect 别名（`madness`/`insanity`）？ | 是（扩展别名表）/ 否（归入 control/dot） | 建议先归入 `control`+`dot`，Wave 3 再评估是否需要专门的心灵伤害类型 |
| Q7 | Wave 2 多 IP 是否审批通过后立刻启动？ | 是 / 等 Wave 1 全部关闭 | **审批通过即可启动**——Wave 2 新增 IP 与 Wave 1 存量 IP 改动零耦合 |

---

## 附录 A — 各 IP ATTRIBUTION.md 公有领域来源

| IP | 原著 | 成书年代 | 作者 | 公有领域确认 |
|---|---|---|---|---|
| 三国演义 | 《三国演义》 | 约 1400 年（明初） | 罗贯中 | ✅ 去世 >600 年 |
| 西游记 | 《西游记》 | 约 1590 年（明万历） | 吴承恩 | ✅ 去世 >400 年 |
| 封神演义 | 《封神演义》 | 约 1620 年（明末） | 许仲琳（有争议） | ✅ 无论作者是谁，距今 >400 年 |
| 北欧神话 | 《埃达》《散文埃达》 | 约 1220 年 | 佚名 / Snorri Sturluson | ✅ Snorri 1241 年去世 |
| 希腊神话 | 荷马史诗等 | 口传（约公元前 8 世纪） | 荷马等（佚名/古代） | ✅ 自古公有 |
| 克苏鲁神话 | Lovecraft 早期作品 | 1917-1937 年 | H.P. Lovecraft | ✅ 1937 年去世，中国 2007 年进入 PD（70 年）；美国 2032 年（95 年），但本项目中国属地优先 |
| 世界历史名将 | 正史记载 | 古代 | 不适用 | ✅ 历史事实不可版权化 |

---

## 附录 B — GDD §2.4 原始框架 vs 本方案差异

| 维度 | GDD §2.4 原始 | 本方案 | 变更理由 |
|---|---|---|---|
| 总英雄数 | 120–200 | **160** | 取中位数，7 个 IP 自然配比后落在此区间 |
| 三国演义配额 | 40–60（含于中国古典 60–90） | **40** | 拆分为三个独立 IP 后，三国独立 40、西游 25、封神 20 |
| 中国古典再拆分 | GDD 统一为"中国古典"一坨 | **拆为三国/西游/封神三个独立 IP** | 三者文学来源不同、角色池独立、ATTRIBUTION 来源不同；合在一起模糊了公有领域声明 |
| 克苏鲁配额 | 15–25 | **15** | 下限取值：可独立成团的角色有限；心灵/疯狂定制成本高 |
| 世界历史名将 | 15–35 | **20** | 中位取值：不同时代/地域各有 2-3 代表即可 |
| 角色配比约束 | support ≥20%、assassin ≥18% | support 19.4%、assassin 23.1% | 差 0.6pp 达标，主理人可微调 |

---

*文档结束 — 待主理人审批后进入执行*
