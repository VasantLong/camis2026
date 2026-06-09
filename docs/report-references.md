# 分析与设计报告 — 项目文档引用索引

> `docs/analysis-design-report.md` 各章节所引用的项目文档与代码源。

## 第 2 章 系统分析

| 报告节 | 引用文档 | 引用代码 |
|--------|---------|----------|
| 2.1.1 参与者识别 | `docs/rbac.md` §1-2（角色-权限矩阵）、`CONTEXT.md`（角色定义） | `app/routers/*.py`（`require_permission` 装饰器） |
| 2.1.2 用例图 | `docs/camis-UML.md` §UC1-UC6（用例规约）、`docs/state-machine.md`（状态-用例对应） | `app/routers/filings.py`、`app/routers/templates.py`、`app/routers/workflows.py` |
| 2.2 领域类图 | `docs/camis-UML.md` §实体模型（Mermaid 类图）、`CONTEXT.md`（实体描述） | `app/models/*.py`（11 个模型文件） |
| 2.3 状态图 | `docs/state-machine.md`（完整状态机 + 子状态机 + 关键规则） | `app/services/workflow_service.py`（`TRANSITION_MATRIX`）、`frontend/src/utils/constants.ts`（状态常量） |

## 第 3 章 系统设计（待编写）

| 报告节 | 引用文档 | 引用代码 |
|--------|---------|----------|
| 3.1 总体设计 | `docs/adr/0001.md`（SOA 架构决策）、`docs/design-process.md` | `app/main.py`、`app/services/` |
| 3.2.1 界面设计 | `docs/frontend.md`、`docs/ui-design-report.md` | `frontend/src/pages/`、`frontend/src/components/` |
| 3.2.2 业务逻辑设计 | `docs/service-design.md`、`docs/camis-UML.md` §SO 顺序图 | `app/services/`（11 个 Service 文件） |
| 3.2.3 数据层设计 | `docs/data-layer.md`、`docs/data-layer-report.md`、`docs/adr/0006.md`（模板系统） | `app/models/`、Alembic migration 链 |

## 第 4 章 系统实现（待编写）

| 报告节 | 引用文档 | 引用代码 |
|--------|---------|----------|
| 4.1 功能实现 | 各 Service 文档、`docs/browser-tests.md` | `app/`、`frontend/` |
| 4.2 系统测试 | `docs/browser-tests.md` | `tests/browser/17_template_flow.py` |
