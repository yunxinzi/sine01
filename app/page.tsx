"use client";

import { ChangeEvent, CSSProperties, useEffect, useMemo, useRef, useState } from "react";\nimport { toPng } from "html-to-image";\nimport JSZip from "jszip";

type StepId = "input" | "define" | "explore" | "select" | "generate" | "deliver";
type Mode = "Fast" | "Balanced" | "Premium";

type UploadMeta = {
  name: string;
  size: number;
  type: string;
};

type Question = {
  id: string;
  label: string;
  helper: string;
  options: string[];
};

type Styleboard = {
  id: string;
  name: string;
  subtitle: string;
  note: string;
  bg: string;
  panel: string;
  ink: string;
  muted: string;
  accent: string;
  accent2: string;
  border: string;
  motif: "grid" | "orbit" | "editorial" | "mono" | "glass" | "paper" | "signal" | "ocean";
};

type DesignSpec = {
  baseStyle: string;
  layoutStyle: string;
  paletteStyle: string;
  imageryStyle: string;
};

type SlideCopy = {
  type: string;
  title: string;
  body: string;
};

type PersistedState = {
  brief: string;
  answers: Record<string, string>;
  selectedStyleId: string;
  designSpec: DesignSpec;
  mode: Mode;
  activeStep: StepId;
  generated: boolean;
  uploads: UploadMeta[];
};

const STORAGE_KEY = "sine01-v01-state";

const SAMPLE_BRIEF = `主题：威德尔海豹仿生冰面爬升航行器设计
用途：海洋装备创新竞赛阶段汇报
受众：船舶与海洋工程方向教师、评审专家
页数：10页左右
内容重点：问题背景、威德尔海豹仿生依据、爬升动作拆解、机械结构映射、关键机构、冰面运动方式、方案创新点、验证计划
希望风格：中文为主，专业、克制、有未来感，但不要“AI霓虹风”
图片：需要真实科研照片感、机械结构示意和少量数据图
要求：先看多套视觉方向，再确定整套风格；最后希望尽可能可编辑。`;

const STEPS: { id: StepId; label: string; short: string }[] = [
  { id: "input", label: "输入", short: "材料与任务" },
  { id: "define", label: "Define", short: "补齐关键约束" },
  { id: "explore", label: "Explore", short: "8 组 Styleboard" },
  { id: "select", label: "Select", short: "锁定设计系统" },
  { id: "generate", label: "Generate", short: "生成整套预览" },
  { id: "deliver", label: "Deliver", short: "导出与交付" }
];

const STYLEBOARDS: Styleboard[] = [
  {
    id: "polar",
    name: "Polar Research",
    subtitle: "极地科研 · 冷静技术感",
    note: "适合学术汇报、研究计划、实验型内容",
    bg: "#eaf3f5",
    panel: "#f8fbfc",
    ink: "#102c36",
    muted: "#58737a",
    accent: "#0f7183",
    accent2: "#8ecbd0",
    border: "#bad2d7",
    motif: "ocean"
  },
  {
    id: "ink",
    name: "Ink Editorial",
    subtitle: "学术编辑 · 强排版",
    note: "标题与论点更有力度，适合答辩与竞赛",
    bg: "#f4f0e8",
    panel: "#fffdf8",
    ink: "#1c1b18",
    muted: "#706a61",
    accent: "#b5442f",
    accent2: "#d9b99b",
    border: "#d9d0c3",
    motif: "editorial"
  },
  {
    id: "navy",
    name: "Deep Navy",
    subtitle: "深海工业 · 高对比",
    note: "适合装备设计、工程方案与产品发布",
    bg: "#071b2a",
    panel: "#0c2638",
    ink: "#f2f7f8",
    muted: "#94abb7",
    accent: "#57c3cf",
    accent2: "#2d6479",
    border: "#244659",
    motif: "grid"
  },
  {
    id: "signal",
    name: "Signal Lab",
    subtitle: "实验室信号 · 数据感",
    note: "适合图表、验证结果、结构参数",
    bg: "#111317",
    panel: "#181b20",
    ink: "#f6f7f9",
    muted: "#9298a2",
    accent: "#d6f84a",
    accent2: "#6b7d22",
    border: "#343941",
    motif: "signal"
  },
  {
    id: "paper",
    name: "Scientific Paper",
    subtitle: "论文图版 · 克制理性",
    note: "更像高质量学术海报与期刊图版",
    bg: "#f7f8f6",
    panel: "#ffffff",
    ink: "#202622",
    muted: "#6e7871",
    accent: "#3c7250",
    accent2: "#bcd1c2",
    border: "#dce2dd",
    motif: "paper"
  },
  {
    id: "blueprint",
    name: "Blueprint",
    subtitle: "工程蓝图 · 结构优先",
    note: "突出机械、尺寸、构造与系统关系",
    bg: "#eaf0f7",
    panel: "#f7faff",
    ink: "#122c4a",
    muted: "#617590",
    accent: "#3567ad",
    accent2: "#a9c1e3",
    border: "#c8d6e8",
    motif: "grid"
  },
  {
    id: "museum",
    name: "Museum Minimal",
    subtitle: "展陈留白 · 图像主导",
    note: "适合照片、渲染图与少字叙事",
    bg: "#eee9df",
    panel: "#faf7f0",
    ink: "#27251f",
    muted: "#7b7568",
    accent: "#8b6a3f",
    accent2: "#c9b99e",
    border: "#d9d0c1",
    motif: "mono"
  },
  {
    id: "aero",
    name: "Aero Glass",
    subtitle: "轻量未来 · 半透明层次",
    note: "适合概念设计、创新赛与产品愿景",
    bg: "#e9effa",
    panel: "rgba(255,255,255,.74)",
    ink: "#15233d",
    muted: "#61708b",
    accent: "#6757d9",
    accent2: "#a8a0ef",
    border: "#c9cdea",
    motif: "glass"
  }
];

const DEFAULT_SPEC: DesignSpec = {
  baseStyle: STYLEBOARDS[0].id,
  layoutStyle: STYLEBOARDS[0].id,
  paletteStyle: STYLEBOARDS[0].id,
  imageryStyle: STYLEBOARDS[0].id
};

const ANSWER_OPTIONS: Record<string, string[]> = {
  scene: ["课程汇报", "学术答辩", "竞赛路演", "商业汇报", "工作总结", "其他"],
  audience: ["老师 / 评委", "同学", "企业管理层", "客户", "公众", "混合受众"],
  pages: ["6–8 页", "9–12 页", "13–18 页", "20 页以上"],
  density: ["图像主导", "图文均衡", "文字信息更完整", "数据 / 图表主导"],
  image: ["真实照片", "科研示意", "3D / 产品渲染", "插画", "混合"],
  editability: ["视觉优先", "视觉与可编辑平衡", "尽量全可编辑"]
};

function bytes(size: number) {
  if (size < 1024) return size + " B";
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB";
  return (size / 1024 / 1024).toFixed(1) + " MB";
}

function adaptiveQuestions(brief: string): Question[] {
  const t = brief.toLowerCase();
  const q: Question[] = [];
  if (!/(答辩|竞赛|汇报|路演|课程|总结|发布)/.test(brief)) {
    q.push({ id: "scene", label: "这套 PPT 用在什么场景？", helper: "场景会直接影响信息密度、节奏和视觉力度。", options: ANSWER_OPTIONS.scene });
  }
  if (!/(老师|评委|专家|客户|管理层|同学|公众)/.test(brief)) {
    q.push({ id: "audience", label: "主要给谁看？", helper: "先确定观看者，再决定表达颗粒度。", options: ANSWER_OPTIONS.audience });
  }
  if (!/(\d+\s*页|页数|分钟)/.test(brief)) {
    q.push({ id: "pages", label: "预期页数或汇报时长？", helper: "V0.1 先用页数控制内容节奏。", options: ANSWER_OPTIONS.pages });
  }
  q.push({ id: "density", label: "你更偏向哪种信息比例？", helper: "这会影响留白、字号、图片占比和图表数量。", options: ANSWER_OPTIONS.density });
  if (!/(照片|渲染|插画|示意|图片)/.test(t)) {
    q.push({ id: "image", label: "希望图片更接近哪种视觉？", helper: "后续图像生成与素材检索会继承这个设定。", options: ANSWER_OPTIONS.image });
  }
  q.push({ id: "editability", label: "最终更看重视觉一致性还是可编辑性？", helper: "V1.0 的重建路由会使用这个约束。", options: ANSWER_OPTIONS.editability });
  return q.slice(0, 6);
}

function styleById(id: string) {
  return STYLEBOARDS.find((s) => s.id === id) || STYLEBOARDS[0];
}

function miniSlide(style: Styleboard, kind: "cover" | "content" | "data", index: number) {
  const rootStyle: CSSProperties = {
    background: style.bg,
    color: style.ink,
    borderColor: style.border
  };

  if (kind === "cover") {
    return (
      <div className={"mini-slide motif-" + style.motif + " mini-variant-" + (index % 4)} style={rootStyle}>
        <div className="mini-kicker" style={{ color: style.accent }}>DESIGN STUDY / 0{index + 1}</div>
        <div className="mini-title">仿生冰面爬升<br />航行器设计</div>
        <div className="mini-rule" style={{ background: style.accent }} />
        <div className="mini-caption" style={{ color: style.muted }}>WEDDELL SEAL · BIOMIMETIC SYSTEM</div>
      </div>
    );
  }

  if (kind === "content") {
    return (
      <div className={"mini-slide motif-" + style.motif + " mini-variant-" + (index % 4)} style={rootStyle}>
        <div className="mini-head">01 / 动作拆解</div>
        <div className="mini-columns">
          <div>
            <div className="mini-line strong" style={{ background: style.ink }} />
            <div className="mini-line" style={{ background: style.muted }} />
            <div className="mini-line short" style={{ background: style.muted }} />
          </div>
          <div className="mini-visual" style={{ background: style.accent2, borderColor: style.accent }}>
            <span style={{ background: style.accent }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={"mini-slide motif-" + style.motif + " mini-variant-" + (index % 4)} style={rootStyle}>
      <div className="mini-head">06 / 结构映射</div>
      <div className="mini-data">
        <div className="mini-donut" style={{ borderColor: style.accent }} />
        <div className="mini-bars">
          {[68, 44, 82].map((w, i) => (
            <div key={i} className="bar-track" style={{ background: style.border }}>
              <span style={{ width: w + "%", background: i === 2 ? style.accent : style.accent2 }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const SAMPLE_SLIDES: SlideCopy[] = [
  { type: "封面", title: "威德尔海豹仿生冰面爬升航行器设计", body: "从极地动物上冰行为提取可工程映射的爬升机制" },
  { type: "问题", title: "冰水界面，是整个任务链最不稳定的一段", body: "低摩擦、湿滑边缘与姿态突变，使传统轮式或单一推进方式难以稳定完成越界。" },
  { type: "依据", title: "为什么选择威德尔海豹作为仿生对象", body: "其上冰过程同时包含柔顺躯干、前部支撑、后部推进与连续重心迁移，具备明确的工程映射价值。" },
  { type: "动作", title: "把上冰动作拆成四个可设计阶段", body: "接近冰缘、前部搭载、躯干抬升、重心越界。每一阶段对应不同的受力与机构需求。" },
  { type: "结构", title: "仿生不是复制外形，而是复制功能关系", body: "柔顺躯干对应可变构型中段；前肢支撑对应抓附/承载模块；后躯摆动对应水下推进与姿态控制。" },
  { type: "机构", title: "中部折弯机构承担最关键的姿态转换", body: "通过主动弯曲降低爬升瞬间的等效抬升高度，并将推进力更有效地转化为跨越冰缘的法向分量。" },
  { type: "冰面", title: "上冰后切换为低阻滑行与辅助转向", body: "冰刀承担低阻承载，升降轮用于低速转向与复杂冰况通过，尾部推进提供持续驱动力。" },
  { type: "创新", title: "创新点来自三个功能耦合，而不是单一新零件", body: "仿生姿态变化、跨介质推进切换、冰刀/轮复合运动共同构成完整任务链。" },
  { type: "验证", title: "先验证“可靠爬升”，再优化冰面效率", body: "优先测试冰缘高度、摩擦系数、入射角与折弯幅度对成功率和峰值载荷的影响。" },
  { type: "结论", title: "把动物的连续动作，变成机器的可控状态", body: "下一阶段进入机构参数化、样机尺寸约束与冰水界面实验设计。" }
];

const GENERIC_SECTIONS: Omit<SlideCopy, "title">[] = [
  { type: "背景", body: "从输入材料中提炼背景、现状与需要解决的核心矛盾。" },
  { type: "问题", body: "把宽泛主题收敛为少数几个需要回答的关键问题。" },
  { type: "目标", body: "明确这套汇报希望观众最终理解、相信或记住什么。" },
  { type: "洞察", body: "将原始材料整理成有层级的核心信息，而不是简单堆砌文本。" },
  { type: "结构", body: "建立内容之间的逻辑关系，让每一页只承担一个主要表达任务。" },
  { type: "证据", body: "集中放置最能支撑观点的数据、案例、文献或事实材料。" },
  { type: "方案", body: "把关键方法、机制或解决思路组织成可视化模块。" },
  { type: "细节", body: "补充实现路径、组成部分、参数或操作要点。" },
  { type: "比较", body: "通过对照呈现差异、取舍和方案边界。" },
  { type: "数据", body: "把高价值数字转成图表或结构化指标，减少大段说明文字。" },
  { type: "案例", body: "用一个具体例子帮助观众把抽象结论落到真实情境。" },
  { type: "流程", body: "呈现任务如何推进、各环节如何衔接以及关键控制点。" },
  { type: "风险", body: "说明限制条件、风险来源与当前尚未解决的问题。" },
  { type: "验证", body: "说明如何证明方案有效，以及下一步需要获得哪些证据。" },
  { type: "价值", body: "集中呈现方案产生的学术、工程、业务或传播价值。" },
  { type: "计划", body: "将后续工作拆成清晰阶段，并标记近期最重要的里程碑。" },
  { type: "总结", body: "回收前文结论，保留三条以内最值得记住的信息。" },
  { type: "结束", body: "用一句清晰的结束语收束整套叙事，并为问答留出空间。" }
];

function resolvePageCount(brief: string, answers: Record<string, string>) {
  const explicit = brief.match(/(\d{1,2})\s*页/);
  if (explicit) return Math.min(20, Math.max(6, Number(explicit[1])));
  const choice = answers.pages;
  if (choice === "6–8 页") return 8;
  if (choice === "9–12 页") return 10;
  if (choice === "13–18 页") return 14;
  if (choice === "20 页以上") return 20;
  return 10;
}

function briefTitle(brief: string) {
  const line = brief
    .split(/\n+/)
    .map((x) => x.trim())
    .find(Boolean) || "未命名演示项目";
  return line.replace(/^(主题|题目|标题)[:：]\s*/, "").slice(0, 48);
}

function buildDemoSlides(brief: string, answers: Record<string, string>): SlideCopy[] {
  const count = resolvePageCount(brief, answers);
  if (/威德尔海豹/.test(brief) && count === 10) return SAMPLE_SLIDES;

  const title = briefTitle(brief);
  const summary = brief.replace(/\s+/g, " ").trim().slice(0, 120);
  const middleNeeded = Math.max(4, count - 2);
  const middle = GENERIC_SECTIONS.slice(0, middleNeeded).map((section, index) => ({
    type: section.type,
    title:
      index === 0 ? "为什么现在需要讨论这个问题" :
      index === 1 ? "把主题收敛为可回答的核心问题" :
      index === 2 ? "这套汇报需要达成什么目标" :
      index === 3 ? "从原始材料中提炼出的关键信息" :
      section.type + " / " + title,
    body: index === 0 && summary ? summary : section.body
  }));

  while (middle.length < middleNeeded) {
    const section = GENERIC_SECTIONS[middle.length % GENERIC_SECTIONS.length];
    middle.push({
      type: section.type,
      title: section.type + " / " + title,
      body: section.body
    });
  }

  return [
    {
      type: "封面",
      title,
      body: "Sine01 V0.1 根据当前 Brief 与设计约束生成的视觉优先演示结构。"
    },
    ...middle,
    {
      type: "结论",
      title: "收束核心结论，并明确下一步",
      body: "回收前文最重要的信息，同时保留后续验证、行动或讨论入口。"
    }
  ].slice(0, count);
}

function SlideVisual({
  style,
  slide,
  index,
  variation,
  layoutId
}: {
  style: Styleboard;
  slide: SlideCopy;
  index: number;
  variation: number;
  layoutId: string;
}) {
  const layoutOffset = Math.max(0, STYLEBOARDS.findIndex((item) => item.id === layoutId)) % 4;
  const mode = (index + variation + layoutOffset) % 4;
  const root: CSSProperties = {
    background: style.bg,
    color: style.ink,
    borderColor: style.border
  };

  return (
    <div className={"slide-canvas motif-" + style.motif} style={root}>
      <div className="slide-topline">
        <span style={{ color: style.accent }}>SINE01 / CONCEPT DECK</span>
        <span style={{ color: style.muted }}>{String(index + 1).padStart(2, "0")} / 10</span>
      </div>

      {index === 0 ? (
        <div className="hero-layout">
          <div className="hero-copy">
            <div className="hero-eyebrow" style={{ color: style.accent }}>BIOMIMETIC MARINE SYSTEM</div>
            <h3>{slide.title}</h3>
            <p style={{ color: style.muted }}>{slide.body}</p>
            <div className="hero-tags">
              <span style={{ borderColor: style.border }}>威德尔海豹</span>
              <span style={{ borderColor: style.border }}>冰水跨介质</span>
              <span style={{ borderColor: style.border }}>机械仿生</span>
            </div>
          </div>
          <div className="hero-object" style={{ background: style.panel, borderColor: style.border }}>
            <div className="orb orb-a" style={{ background: style.accent }} />
            <div className="orb orb-b" style={{ borderColor: style.accent2 }} />
            <div className="vehicle" style={{ background: style.ink }}>
              <span style={{ background: style.accent }} />
            </div>
          </div>
        </div>
      ) : mode === 1 ? (
        <div className="split-layout">
          <div className="copy-block">
            <span className="slide-label" style={{ color: style.accent }}>{slide.type}</span>
            <h3>{slide.title}</h3>
            <p style={{ color: style.muted }}>{slide.body}</p>
          </div>
          <div className="diagram-card" style={{ background: style.panel, borderColor: style.border }}>
            <div className="diag-line" style={{ background: style.border }} />
            <div className="diag-node n1" style={{ background: style.accent }} />
            <div className="diag-node n2" style={{ background: style.accent2 }} />
            <div className="diag-node n3" style={{ background: style.ink }} />
            <div className="diag-caption" style={{ color: style.muted }}>mechanism / motion / load</div>
          </div>
        </div>
      ) : mode === 2 ? (
        <div className="statement-layout">
          <span className="slide-label" style={{ color: style.accent }}>{slide.type}</span>
          <h3>{slide.title}</h3>
          <div className="statement-grid">
            {["功能映射", "姿态控制", "任务闭环"].map((x, i) => (
              <div key={x} className="metric-card" style={{ background: style.panel, borderColor: style.border }}>
                <b style={{ color: style.accent }}>0{i + 1}</b>
                <span>{x}</span>
                <small style={{ color: style.muted }}>{i === 0 ? "BIO → MECH" : i === 1 ? "POSE / LOAD" : "WATER / ICE"}</small>
              </div>
            ))}
          </div>
          <p className="statement-note" style={{ color: style.muted }}>{slide.body}</p>
        </div>
      ) : mode === 3 ? (
        <div className="data-layout">
          <div className="copy-block narrow">
            <span className="slide-label" style={{ color: style.accent }}>{slide.type}</span>
            <h3>{slide.title}</h3>
            <p style={{ color: style.muted }}>{slide.body}</p>
          </div>
          <div className="chart-card" style={{ background: style.panel, borderColor: style.border }}>
            <div className="chart-meta">
              <span>验证优先级</span><b style={{ color: style.accent }}>01</b>
            </div>
            {[84, 62, 46, 30].map((w, i) => (
              <div className="chart-row" key={i}>
                <span style={{ color: style.muted }}>P{i + 1}</span>
                <div style={{ background: style.border }}>
                  <i style={{ width: w + "%", background: i === 0 ? style.accent : style.accent2 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="quote-layout">
          <span className="slide-label" style={{ color: style.accent }}>{slide.type}</span>
          <h3>{slide.title}</h3>
          <p style={{ color: style.muted }}>{slide.body}</p>
          <div className="long-rule" style={{ background: style.accent }} />
          <small style={{ color: style.muted }}>Design principle / 2026</small>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [brief, setBrief] = useState("");
  const [uploads, setUploads] = useState<UploadMeta[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [activeStep, setActiveStep] = useState<StepId>("input");
  const [selectedStyleId, setSelectedStyleId] = useState(STYLEBOARDS[0].id);
  const [designSpec, setDesignSpec] = useState<DesignSpec>(DEFAULT_SPEC);
  const [mode, setMode] = useState<Mode>("Balanced");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [variation, setVariation] = useState(0);
  const [slideVariation, setSlideVariation] = useState<Record<number, number>>({});
  const [hydrated, setHydrated] = useState(false);\n  const [exportingPng, setExportingPng] = useState(false);\n  const slideRefs = useRef<(HTMLDivElement | null)[]>([]);

  const questions = useMemo(() => adaptiveQuestions(brief), [brief]);
  const slides = useMemo(() => buildDemoSlides(brief, answers), [brief, answers]);
  const selectedStyle = styleById(selectedStyleId);
  const finalStyle = useMemo(() => {
    const palette = styleById(designSpec.paletteStyle);
    const layout = styleById(designSpec.layoutStyle);
    const imagery = styleById(designSpec.imageryStyle);
    return {
      ...styleById(designSpec.baseStyle),
      bg: palette.bg,
      panel: palette.panel,
      ink: palette.ink,
      muted: palette.muted,
      accent: palette.accent,
      accent2: palette.accent2,
      border: palette.border,
      motif: imagery.motif,
      name: styleById(designSpec.baseStyle).name,
      subtitle: layout.subtitle
    } as Styleboard;
  }, [designSpec]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as Partial<PersistedState>;
        if (saved.brief) setBrief(saved.brief);
        if (saved.answers) setAnswers(saved.answers);
        if (saved.selectedStyleId) setSelectedStyleId(saved.selectedStyleId);
        if (saved.designSpec) setDesignSpec(saved.designSpec);
        if (saved.mode) setMode(saved.mode);
        if (saved.activeStep) setActiveStep(saved.activeStep);
        if (saved.generated) setGenerated(saved.generated);
        if (saved.uploads) setUploads(saved.uploads);
      }
    } catch {
      // Ignore malformed local state and start clean.
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const state: PersistedState = {
      brief,
      answers,
      selectedStyleId,
      designSpec,
      mode,
      activeStep,
      generated,
      uploads
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [brief, answers, selectedStyleId, designSpec, mode, activeStep, generated, uploads, hydrated]);

  function loadSample() {
    setBrief(SAMPLE_BRIEF);
    setAnswers({
      density: "图文均衡",
      editability: "视觉与可编辑平衡"
    });
    setActiveStep("define");
  }

  function onFiles(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    setUploads(files.map((f) => ({ name: f.name, size: f.size, type: f.type || "unknown" })));
  }

  function chooseStyle(id: string) {
    setSelectedStyleId(id);
    setDesignSpec({
      baseStyle: id,
      layoutStyle: id,
      paletteStyle: id,
      imageryStyle: id
    });
  }

  function reset() {
    localStorage.removeItem(STORAGE_KEY);
    setBrief("");
    setUploads([]);
    setAnswers({});
    setActiveStep("input");
    setSelectedStyleId(STYLEBOARDS[0].id);
    setDesignSpec(DEFAULT_SPEC);
    setMode("Balanced");
    setGenerated(false);
    setVariation(0);
    setSlideVariation({});
  }

  function exportJson() {
    const payload = {
      version: "0.1",
      sourceBrief: brief,
      uploads,
      answers,
      generationMode: mode,
      designSpec,
      style: finalStyle,
      slides
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sine01-project.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function exportPngZip() {
    if (!generated) return;
    setExportingPng(true);
    try {
      const zip = new JSZip();
      for (let index = 0; index < slides.length; index += 1) {
        const wrap = slideRefs.current[index];
        const canvas = wrap?.querySelector(".slide-canvas") as HTMLElement | null;
        if (!canvas) continue;
        const dataUrl = await toPng(canvas, {
          pixelRatio: 2,
          cacheBust: true,
          backgroundColor: finalStyle.bg
        });
        const base64 = dataUrl.split(",")[1];
        zip.file("slide-" + String(index + 1).padStart(2, "0") + ".png", base64, { base64: true });
      }
      const blob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sine01-visual-deck.zip";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportingPng(false);
    }
  }

  function go(step: StepId) {
    setActiveStep(step);
    window.setTimeout(() => {
      document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 30);
  }

  const answeredCount = questions.filter((q) => answers[q.id]).length;
  const canExplore = brief.trim().length >= 16;
  const canGenerate = Boolean(selectedStyleId);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><span /></div>
          <div>
            <b>Sine01</b>
            <small>visual-first presentation workflow</small>
          </div>
        </div>
        <div className="top-actions">
          <span className="mode-chip">{mode}</span>
          <button className="ghost-btn" onClick={() => setSettingsOpen(true)}>设置</button>
          <button className="ghost-btn" onClick={reset}>重置</button>
        </div>
      </header>

      <div className="workspace" id="workspace">
        <aside className="rail">
          <div className="rail-caption">WORKFLOW / V0.1</div>
          <nav>
            {STEPS.map((step, index) => {
              const activeIndex = STEPS.findIndex((x) => x.id === activeStep);
              const state = index < activeIndex ? "done" : index === activeIndex ? "active" : "";
              return (
                <button key={step.id} className={"rail-step " + state} onClick={() => go(step.id)}>
                  <span className="step-index">{state === "done" ? "✓" : String(index + 1).padStart(2, "0")}</span>
                  <span><b>{step.label}</b><small>{step.short}</small></span>
                </button>
              );
            })}
          </nav>
          <div className="rail-foot">
            <span className="status-dot" />
            <div><b>Demo engine ready</b><small>AI provider will be added behind server routes.</small></div>
          </div>
        </aside>

        <section className="main-stage">
          {activeStep === "input" && (
            <section className="stage-panel">
              <div className="stage-heading">
                <div>
                  <span className="eyebrow">01 / INPUT</span>
                  <h1>先把“做什么”说清楚，<br />再谈怎么设计。</h1>
                </div>
                <p>输入原始材料、任务描述或直接粘贴大段文本。V0.1 不假装已经完成文件解析：上传文件先保留元数据，文本输入可完整进入工作流。</p>
              </div>

              <div className="input-grid">
                <div className="brief-card">
                  <label>项目简报 / 原始内容</label>
                  <textarea
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    placeholder="例如：我要做一套 10 页左右的竞赛汇报 PPT，主题是……"
                  />
                  <div className="brief-footer">
                    <span>{brief.length} 字符</span>
                    <button className="text-btn" onClick={loadSample}>加载示例项目</button>
                  </div>
                </div>
                <label className="upload-card">
                  <input type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md,image/*" onChange={onFiles} />
                  <div className="upload-icon">＋</div>
                  <b>补充上传材料</b>
                  <p>PDF / DOCX / PPTX / TXT / MD / 图片</p>
                  <small>当前版本记录文件信息；深度解析接入 V0.2 server pipeline。</small>
                </label>
              </div>

              {uploads.length > 0 && (
                <div className="file-strip">
                  {uploads.map((file) => (
                    <div className="file-pill" key={file.name + file.size}>
                      <span>FILE</span>
                      <b>{file.name}</b>
                      <small>{bytes(file.size)}</small>
                    </div>
                  ))}
                </div>
              )}

              <div className="stage-actions">
                <div>
                  <small>建议至少提供：主题 + 使用场景 + 核心内容。</small>
                </div>
                <button className="primary-btn" disabled={!canExplore} onClick={() => go("define")}>开始理解需求</button>
              </div>
            </section>
          )}

          {activeStep === "define" && (
            <section className="stage-panel">
              <div className="stage-heading compact">
                <div>
                  <span className="eyebrow">02 / DEFINE</span>
                  <h1>只追问真正影响设计的变量。</h1>
                </div>
                <p>问题会根据你已经写进简报的内容自动减少。不是固定问卷，也不会重复问你已经说明的事情。</p>
              </div>

              <div className="question-list">
                {questions.map((q, index) => (
                  <article className="question-card" key={q.id}>
                    <div className="question-no">{String(index + 1).padStart(2, "0")}</div>
                    <div className="question-copy">
                      <h3>{q.label}</h3>
                      <p>{q.helper}</p>
                      <div className="option-row">
                        {q.options.map((option) => (
                          <button
                            key={option}
                            className={answers[q.id] === option ? "choice active" : "choice"}
                            onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: option }))}
                          >
                            {option}
                          </button>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>

              <div className="stage-actions sticky-actions">
                <div>
                  <b>{answeredCount} / {questions.length}</b>
                  <small>未回答项会采用安全默认值，你可以直接继续。</small>
                </div>
                <button className="primary-btn" onClick={() => go("explore")}>生成 8 组 Styleboard</button>
              </div>
            </section>
          )}

          {activeStep === "explore" && (
            <section className="stage-panel wide">
              <div className="stage-heading compact">
                <div>
                  <span className="eyebrow">03 / EXPLORE</span>
                  <h1>不是 8 张封面，而是 8 套真正不同的设计方向。</h1>
                </div>
                <p>每套 Styleboard 同时展示封面、内容页、结构/数据页，避免只看封面做错误选择。</p>
              </div>

              <div className="styleboard-grid">
                {STYLEBOARDS.map((style, index) => (
                  <button
                    key={style.id}
                    className={selectedStyleId === style.id ? "styleboard selected" : "styleboard"}
                    onClick={() => chooseStyle(style.id)}
                  >
                    <div className="styleboard-preview">
                      {miniSlide(style, "cover", index)}
                      {miniSlide(style, "content", index)}
                      {miniSlide(style, "data", index)}
                    </div>
                    <div className="styleboard-meta">
                      <div>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <h3>{style.name}</h3>
                      </div>
                      <b>{style.subtitle}</b>
                      <p>{style.note}</p>
                    </div>
                  </button>
                ))}
              </div>

              <div className="stage-actions sticky-actions">
                <div><b>已选：{selectedStyle.name}</b><small>{selectedStyle.subtitle}</small></div>
                <button className="primary-btn" onClick={() => go("select")}>锁定 / 混合设计方向</button>
              </div>
            </section>
          )}

          {activeStep === "select" && (
            <section className="stage-panel">
              <div className="stage-heading compact">
                <div>
                  <span className="eyebrow">04 / SELECT</span>
                  <h1>允许“混搭”，但最终只输出一套 Design Spec。</h1>
                </div>
                <p>你可以保留主风格，同时把版式、配色、图像语言分别借用另一套方案。生成阶段只读取锁定后的设计规范。</p>
              </div>

              <div className="spec-layout">
                <div className="spec-controls">
                  {[
                    ["baseStyle", "主风格", "控制整体气质、字体尺度与节奏"],
                    ["layoutStyle", "版式语言", "控制留白、网格、标题和信息块关系"],
                    ["paletteStyle", "配色系统", "控制背景、正文、强调色和边框"],
                    ["imageryStyle", "图像语言", "控制画面纹理、示意图与视觉母题"]
                  ].map(([key, label, helper]) => (
                    <label className="spec-row" key={key}>
                      <span><b>{label}</b><small>{helper}</small></span>
                      <select
                        value={designSpec[key as keyof DesignSpec]}
                        onChange={(e) => setDesignSpec((prev) => ({ ...prev, [key]: e.target.value }))}
                      >
                        {STYLEBOARDS.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                    </label>
                  ))}
                </div>

                <div className="spec-preview">
                  <div className="spec-preview-head">
                    <span>LIVE DESIGN SPEC</span>
                    <b>{styleById(designSpec.baseStyle).name}</b>
                  </div>
                  <SlideVisual style={finalStyle} slide={slides[Math.min(4, slides.length - 1)]} index={4} variation={variation} layoutId={designSpec.layoutStyle} />
                  <div className="token-row">
                    {[finalStyle.bg, finalStyle.panel, finalStyle.ink, finalStyle.accent, finalStyle.accent2].map((c) => (
                      <span key={c} style={{ background: c, borderColor: finalStyle.border }} title={c} />
                    ))}
                  </div>
                </div>
              </div>

              <div className="stage-actions">
                <div><small>Design Spec 会成为后续 Generate / Rebuild / Evaluate 的唯一视觉输入。</small></div>
                <button className="primary-btn" disabled={!canGenerate} onClick={() => { setGenerated(true); go("generate"); }}>生成完整 {slides.length} 页预览</button>
              </div>
            </section>
          )}

          {activeStep === "generate" && (
            <section className="stage-panel wide">
              <div className="stage-heading compact">
                <div>
                  <span className="eyebrow">05 / GENERATE</span>
                  <h1>先生成完整视觉，再考虑拆成多少可编辑对象。</h1>
                </div>
                <p>这里验证整套节奏、跨页一致性和内容表达。单页可重生成，整套也可重新变体；当前使用本地 demo renderer，不伪装成真实 AI 生成。</p>
              </div>

              <div className="deck-toolbar">
                <div>
                  <span className="live-dot" /> {slides.length} slides generated
                  <small> · {finalStyle.name} · {mode}</small>
                </div>
                <button className="ghost-btn" onClick={() => setVariation((v) => v + 1)}>重新生成整套变体</button>
              </div>

              <div className="deck-grid">
                {slides.map((slide, index) => (
                  <article className="deck-item" key={slide.title}>
                    <div className="deck-item-head">
                      <div><span>{String(index + 1).padStart(2, "0")}</span><b>{slide.type}</b></div>
                      <button
                        className="tiny-btn"
                        onClick={() => setSlideVariation((prev) => ({ ...prev, [index]: (prev[index] || 0) + 1 }))}
                      >
                        单页变体
                      </button>
                    </div>
                    <div
                      className="capture-wrap"
                      ref={(node) => {
                        slideRefs.current[index] = node;
                      }}
                    >
                      <SlideVisual
                        style={finalStyle}
                        slide={slide}
                        index={index}
                        variation={variation + (slideVariation[index] || 0)}
                        layoutId={designSpec.layoutStyle}
                      />
                    </div>
                  </article>
                ))}
              </div>

              <div className="stage-actions sticky-actions">
                <div><b>视觉预览完成</b><small>下一版将加入真实图片生成、内容模型与逐页 QA。</small></div>
                <button className="primary-btn" onClick={() => go("deliver")}>进入交付</button>
              </div>
            </section>
          )}

          {activeStep === "deliver" && (
            <section className="stage-panel">
              <div className="stage-heading compact">
                <div>
                  <span className="eyebrow">06 / DELIVER</span>
                  <h1>V0.1 先把“可验证的交付”做真实。</h1>
                </div>
                <p>现在可以导出项目 JSON、打包 10 页 PNG 视觉稿、使用浏览器打印为 PDF。Editable PPTX、Rebuild 和 Visual QA 明确放到 V1.0，不做假按钮。</p>
              </div>

              <div className="deliver-grid">
                <article className="deliver-card ready">
                  <span>READY</span>
                  <h3>Project JSON</h3>
                  <p>保存 Brief、问答、Styleboard、Design Spec 与 10 页内容结构。</p>
                  <button className="primary-btn" onClick={exportJson}>导出 JSON</button>
                </article>
                <article className="deliver-card ready">
                  <span>READY</span>
                  <h3>PNG Deck ZIP</h3>
                  <p>将已经批准的 {slides.length} 页视觉稿按 2× 像素密度渲染为 PNG，并一次性打包下载。</p>
                  <button className="primary-btn" disabled={!generated || exportingPng} onClick={exportPngZip}>
                    {exportingPng ? "正在渲染…" : "导出 " + slides.length + " 页 PNG"}
                  </button>
                </article>
                <article className="deliver-card ready">
                  <span>READY</span>
                  <h3>Printable Preview</h3>
                  <p>使用浏览器打印当前页面，可保存为 PDF 作为阶段预览。</p>
                  <button className="primary-btn" onClick={() => window.print()}>打印 / 保存 PDF</button>
                </article>
                <article className="deliver-card future">
                  <span>V1.0</span>
                  <h3>Editable PPTX</h3>
                  <p>接入 Rebuild Router：简单页原生对象、中等页图文分层、复杂页高背景占比。</p>
                  <div className="future-badge">NEXT</div>
                </article>
                <article className="deliver-card future">
                  <span>V1.0</span>
                  <h3>Visual QA</h3>
                  <p>渲染 PPTX 与批准视觉稿比对；失败时降低拆分粒度并自动重建。</p>
                  <div className="future-badge">NEXT</div>
                </article>
              </div>

              <div className="architecture-note">
                <span>WORKFLOW</span>
                <b>Define · Explore · Select · Generate · Rebuild · Evaluate · Deliver</b>
                <p>当前 V0.1 已跑通前四段与基础 Deliver；下一阶段重点不是加页面，而是接真实 AI provider 和 PPT 重建闭环。</p>
              </div>
            </section>
          )}
        </section>

        <aside className="inspector">
          <div className="inspector-title">RUN INSPECTOR</div>
          <section>
            <span>SOURCE</span>
            <b>{brief ? "Brief loaded" : "Waiting for brief"}</b>
            <small>{brief ? brief.slice(0, 72) + (brief.length > 72 ? "…" : "") : "输入任务后开始。"}</small>
          </section>
          <section>
            <span>DEFINE</span>
            <b>{answeredCount} answered</b>
            <small>{questions.length} adaptive questions in this run</small>
          </section>
          <section>
            <span>DESIGN SPEC</span>
            <b>{styleById(designSpec.baseStyle).name}</b>
            <div className="mini-token-row">
              {[finalStyle.bg, finalStyle.ink, finalStyle.accent, finalStyle.accent2].map((c) => <i key={c} style={{ background: c }} />)}
            </div>
          </section>
          <section>
            <span>GENERATION</span>
            <b>{generated ? slides.length + " / " + slides.length + " previewed" : "Not generated"}</b>
            <small>Mode: {mode}</small>
          </section>
          <section>
            <span>STATE</span>
            <b>Local autosave</b>
            <small>刷新页面不会丢失当前选择。</small>
          </section>
        </aside>
      </div>

      {settingsOpen && (
        <div className="modal-backdrop" onMouseDown={() => setSettingsOpen(false)}>
          <div className="settings-panel" onMouseDown={(e) => e.stopPropagation()}>
            <div className="settings-head">
              <div><span className="eyebrow">GENERATION MODE</span><h2>生成策略</h2></div>
              <button className="ghost-btn" onClick={() => setSettingsOpen(false)}>关闭</button>
            </div>
            <p>V0.1 只记录生成策略并影响后续 AI provider 参数。默认 Balanced。</p>
            <div className="mode-list">
              {([
                ["Fast", "更少迭代，优先速度与成本"],
                ["Balanced", "默认：质量、速度、可编辑性平衡"],
                ["Premium", "更多候选与 QA 轮次，优先质量"]
              ] as [Mode, string][]).map(([name, desc]) => (
                <button key={name} className={mode === name ? "mode-option active" : "mode-option"} onClick={() => setMode(name)}>
                  <span>{name}</span><small>{desc}</small>
                </button>
              ))}
            </div>
            <div className="settings-foot">
              <span>API keys will never be stored in browser state.</span>
              <button className="primary-btn" onClick={() => setSettingsOpen(false)}>保存设置</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
