# NoPC CAE Cloud Bridge v0.2.0

**在 AI 自带 Python/终端环境中执行真正的、可审核的有限元计算。** 本包为可安装 Agent Skill + Python CLI + 自主求解器 + 条件式开源求解器适配器；不使用付费 VPS、GitHub Actions 或其他外部计算服务。GitHub/Drive 仅可存储代码、检查点与结果。

> 与此前 **NoPC CAE Skill v0.2.0** 不同：这里是 **Cloud Bridge v0.2.0**。两者独立。本仓库由上一版 Cloud Bridge v0.1.0 升级而来，旧 NoPC CAE Skill v0.2.0 的 ZIP 没有在本运行环境中取得可修改源码，因此未声称已合并、迁移或覆盖旧版功能。

## 当前能力与真实状态

| 功能 | 是否实际执行/验证 | 范围说明 |
|---|---|---|
| 三维 C3D4 自主有限元计算 | **已执行** | 矩形棱柱、线弹性、小应变、静力；可选择 quick / research（均匀场网格检查） |
| 严格读取并计算 `.inp` | **已执行** | 节点、C3D4 单元、单材料各向同性、集合、零位移约束、集中力、单静力分析步；SI 单位必须人工确认 |
| Abaqus `.for` 文件分析 | **已执行静态审计** | 识别 UMAT/VUMAT 等接口候选；**不编译、不移植、不运行** |
| 多阶段任务与人工恢复 | **已执行** | `run-job` 保存尝试记录、复用已完成结果，失败可 `--resume` 整体重跑；**不支持求解器内部真正的 checkpoint** |
| 交付文件完整性 + 数值二次复核 | **已执行** | SHA256、ZIP 安全解包、场量-本构复核、INP 内力-反力-能量重新组装；不是实验验证 |
| CalculiX CCX | **仅流程接口与模拟可执行文件测试** | 需 Agent 当前环境真实安装兼容求解器，必须独立验证结果 |
| OpenRadioss Starter/Engine | **仅流程接口与模拟可执行文件测试** | 尚未在当前环境真实运行外部求解器，严禁声称已完成冲击仿真 |
| 复合材料 3D 冲击、CZM/Hashin/VUMAT | **未实现** | 不得用 3D 弹性或材料点试验冒充冲击损伤 |

## 直接安装

Python 3.10+、NumPy、SciPy，建议 pytest + matplotlib：

```bash
python -m pip install -e '.[viz,test]'
python -m nopc_bridge doctor
python -m pytest -q tests
```

已自带 NumPy/SciPy 且不方便安装时可在项目目录使用 `PYTHONPATH=src python -m nopc_bridge ...`。

## 从 JSON 真正计算

```bash
python -m nopc_bridge preflight examples/tension3d.json
python -m nopc_bridge run examples/tension3d.json --mode research --out runs/research
python -m nopc_bridge verify runs/research
python -m nopc_bridge bundle runs/research --out research.zip
python -m nopc_bridge verify research.zip
```

`research` 为 3 档均匀拉伸网格的单值检查，不是任意复杂结构的工程级收敛性证明。`engineering` 模式拒绝自动获得工业认证。

## Abaqus `.inp` 的严格受限计算（新增）

```bash
python -m nopc_bridge audit-inp examples/minimal_ccx.inp
python -m nopc_bridge solve-inp examples/minimal_ccx.inp --units SI --out runs/inp_example
python -m nopc_bridge verify runs/inp_example
```

**请首先确认** `.inp` 输入节点坐标以 **米** 为单位、载荷 **牛顿**、材料杨氏模量 **帕斯卡**。Abaqus INP 自身不声明单位；当前桥接版本只接受明确的 `--units SI`，不默默转换毫米或 MPa。

严格支持：`*NODE`、`*ELEMENT,TYPE=C3D4`、`*MATERIAL`、常数 `*ELASTIC`、`*SOLID SECTION`、`*NSET/*ELSET`、零位移 `*BOUNDARY`、`*CLOAD`、一个 `*STEP/*STATIC`，以及部分无副作用输出请求。遇到 `*DYNAMIC`、`*USER MATERIAL`、`*CONTACT`、复合材料、`*INCLUDE`、多分析步、非零位移等立即拒绝，**不允许偷偷忽略后计算**。几何不规则或单元定向错误同样会拒绝。完整输入副本 `source.inp` 与节点/单元数据同时封存，便于复核。

## 保存任务、重复运行或恢复中断（新增）

```bash
python -m nopc_bridge run-job examples/tension3d.json --mode quick --out jobs/tension
python -m nopc_bridge run-job examples/tension3d.json --mode quick --out jobs/tension --resume
python -m nopc_bridge verify jobs/tension
python -m nopc_bridge bundle jobs/tension --out tension_job.zip
```

写入 `journal.json` + `attempts/attempt_001` 等独立目录。若已完成且校验通过，第二条命令只读取既有结果、不重新计算；若之前出错，保留旧错误记录并创建新尝试，**重跑整个有限元问题**。这不是在中断点恢复迭代器/显式动力学状态。若 Codex 会话后文件消失，请把 `jobs/tension` 完整保存至允许的 GitHub/Drive 私有存储，恢复时在新执行环境读取文件；系统不会自动突破平台存储或资源限制。

## 外部求解器连接（仅在真实安装后尝试）

```bash
python -m nopc_bridge run-ccx examples/minimal_ccx.inp --out runs/ccx --timeout 300
python -m nopc_bridge run-radioss model_0000.rad model_0001.rad --root /path/to/OpenRadioss --out runs/radioss
```

这两条指令**没有**在本轮验证中运行真实 CCX/OpenRadioss 二进制。本仓库的自动测试使用模拟可执行文件验证调用、失败和文件完整性。仅生成 FRD 或其他输出文件不构成物理结果验证。外部求解器和 OpenRadioss 材料模型的许可证及文档应单独审核。

## 手机上从 Codex Cloud 使用

1. 将 ZIP 解压后的工程目录推送到 GitHub 仓库（仓库只用来存储，勿开启 Actions 计算）。
2. 在手机上的 Codex Cloud 选择仓库，创建新的云端代码任务，先读取 `AGENTS.md` 和 `SKILL.md`。
3. 运行 `bash scripts/setup_codex.sh`（如平台允许），接着执行 `pytest` 和 `doctor`。只有确认真实权限后才尝试 `--install-ccx`。
4. 直接说：**“只使用当前 Codex Cloud 自带算力，先运行测试和已有标准算例，再使用我上传的 .inp 文件；对不支持的物理问题直接指出，返回带校验的结果 ZIP。”**
5. 把 `runs`、`jobs`、ZIP 下载至手机或保存到外部**存储**。不要把 Codex 云端任务当成无限时长的 VPS。

目前的所有运行证据来自**当前会话的 ChatGPT Python 容器**，并未在你的 Codex Cloud 账号环境实测。两种执行环境不可混同。

## 安全与可复现原则

- `verify` 检验文件哈希和数值自洽，并不等价于物理、实验、网格无关性或工业级验证；用户可以重新运行算例逐项复核。
- 未知用户 Fortran 不编译、不执行；输入文件不可信，`*INCLUDE` 的越界/符号链接路径被限制；ZIP 拒绝不安全成员和异常大解压规模。
- 结果文件包含 `case_used.json`、`fields.npz`、`result.vtk`、可选 PNG、独立 HTML、`REPORT.md`、`manifest.json`，`solve-inp` 还附带 `source.inp`。
- 原创部分 MIT 许可，第三方软件有独立许可；公开仓库禁止上传无再分发授权的 Fortran 源码、未公开科研数据或密钥。

详见 `docs/V02_VALIDATION.md`、`docs/INTEGRATION.md` 和 `docs/LIMITATIONS.md`。
