"""创建预设测试活动，覆盖 12 种状态 + 附件 + 完整属性。幂等。"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.auth import hash_password
from app.database import async_session
from app.models.activity import (
    Activity, ActivityPlan, ActivityStatusLog, ApprovalRecord,
    ImplementationRecord, SecurityPlan,
)
from app.models.document import Document
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.services.minio_client import upload_file


def _make_pdf(title: str, text: str) -> bytes:
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 780, title)
    c.setFont("Helvetica", 11)
    y = 740
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = 780
    c.save()
    return buf.getvalue()


def _make_xlsx(title: str, rows: list[list[str]]) -> bytes:
    """生成最小有效 XLSX（ZIP + XML）。"""
    import zipfile
    from io import BytesIO

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ))
        zf.writestr("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ))
        zf.writestr("xl/workbook.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>'
        ))
        zf.writestr("xl/_rels/workbook.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ))
        rows_xml = "".join(
            "<row>" + "".join(f"<c t=\"inlineStr\"><is><t>{v}</t></is></c>" for v in row) + "</row>"
            for row in rows
        )
        zf.writestr("xl/worksheets/sheet1.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{rows_xml}</sheetData></worksheet>'
        ))
    return buf.getvalue()


def _make_csv(rows: list[list[str]]) -> bytes:
    return "\n".join(",".join(v.replace(",", "，") for v in row) for row in rows).encode("utf-8")


def _make_docx(title: str, body: str) -> bytes:
    """生成最小有效 DOCX（ZIP + WordprocessingML）。"""
    import zipfile
    from io import BytesIO

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        ))
        zf.writestr("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>'
        ))
        paragraphs = "".join(
            f'<w:p><w:r><w:t xml:space="preserve">{line}</w:t></w:r></w:p>'
            for line in body.split("\n")
        )
        zf.writestr("word/document.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body>{paragraphs}</w:body></w:document>'
        ))
    return buf.getvalue()


def _make_jpg() -> bytes:
    """生成 1x1 白色 JPEG。"""
    import struct
    from io import BytesIO

    buf = BytesIO()
    # SOI
    buf.write(b'\xff\xd8')
    # APP0
    buf.write(b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
    # DQT
    buf.write(b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342')
    # SOF0
    buf.write(b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00')
    # DHT
    buf.write(b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b')
    # SOS
    buf.write(b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2\xcf \xff\xd9')
    return buf.getvalue()


# ── activity definitions ──
# (name, type, location, sponsor, estimated_days, deadline_days, target_status)
# days > 0 = future, days < 0 = past, days = 0 = today
ACTIVITIES = [
    ("2026 校园文化节",     "大型", "体育馆",   "校团委",  30, 20, "待设计方案"),
    ("安全生产月启动仪式",  "大型", "会议中心", "安监局",  25, 15, "待安保方案设计"),
    ("社区志愿服务日",      "小型", "市民广场", "街道办",  20, 10, "待备案申请"),
    ("年度总结表彰大会",    "大型", "大礼堂",   "总工会",  15,  5, "备案材料已交接"),
    ("网络安全培训讲座",    "中型", "报告厅",   "网信办",  10,  3, "审批通过"),
    ("职工运动会",          "大型", "体育场",   "工会",     7,  1, "审批通过-待举办"),
    ("春节联欢晚会",        "大型", "文化宫",   "文化局",   0,-10, "举办中"),
    ("科普进社区活动",      "小型", "社区中心", "科协",    -5,-15, "已结束"),
    ("法治宣传周活动",      "中型", "法治广场", "司法局",   8, -2, "待补充备案材料"),
    ("青年创新创业大赛",    "大型", "会展中心", "人社局", -10,-20, "不通过/已终止"),
    ("绿色环保公益行",      "小型", "滨江公园", "环保局",   5, -2, "已取消"),
    ("全民读书月活动",      "中型", "图书馆",   "文化局",  60, -5, "已延期"),
]

# which sub-records each target status needs
STATUS_NEEDS = {
    "待设计方案":        [],
    "待安保方案设计":     ["plan"],
    "待备案申请":        ["plan", "security_plan"],
    "备案材料已交接":     ["plan", "security_plan"],
    "审批通过":          ["plan", "security_plan", "approval"],
    "审批通过-待举办":    ["plan", "security_plan", "approval"],
    "举办中":            ["plan", "security_plan", "approval"],
    "已结束":            ["plan", "security_plan", "approval"],
    "待补充备案材料":     ["plan", "security_plan", "approval"],
    "不通过/已终止":      ["plan", "security_plan", "approval"],
    "已取消":            ["plan"],
    "已延期":            ["plan"],
}


async def seed():
    async with async_session() as db:
        # ── ensure users ──
        promoter = await _ensure_user(db, "promoter", "promoter@test.com", ["Promoter"])
        security = await _ensure_user(db, "security", "security@test.com",
                                       ["SecurityOfficer", "SecurityManager"])
        liaison = await _ensure_user(db, "liaison", "liaison@test.com", ["GovLiaison"])

        # ── check existing ──
        names = [a[0] for a in ACTIVITIES]
        existing = await db.execute(select(Activity).where(Activity.name.in_(names)))
        if existing.scalars().all():
            print("skip: activities already seeded")
            return

        now = datetime.now(timezone.utc)

        for name, atype, location, sponsor, est_days, dl_days, target in ACTIVITIES:
            estimated = now + timedelta(days=est_days)
            deadline = now + timedelta(days=dl_days)

            activity = Activity(
                name=name,
                type=atype,
                estimated_time=estimated,
                location=location,
                sponsor=sponsor,
                deadline=deadline,
                status="待设计方案",
                owner_id=promoter.id,
                designer_id=promoter.id,
            )
            db.add(activity)
            await db.flush()

            needs = STATUS_NEEDS.get(target, [])

            if "plan" in needs:
                plan_text = f"《{name}》活动方案\n主办方：{sponsor}\n地点：{location}\n类型：{atype}\n预计时间：{estimated}\n审批截止：{deadline}"
                plan_bytes = _make_pdf(f"《{name}》活动方案", plan_text)
                plan_path = f"activities/{activity.id}/{uuid4().hex}.pdf"
                await upload_file(plan_path, plan_bytes, "application/pdf")

                _add_doc(db, activity.id, promoter.id,
                         f"{name}_活动方案.pdf", plan_path,
                         len(plan_bytes), "application/pdf", ["方案"])

                db.add(ActivityPlan(
                    activity_id=activity.id,
                    content=plan_text,
                    attachment_url=plan_path,
                    submit_time=now,
                    designer_id=promoter.id,
                    is_overdue=False,
                ))
                await db.flush()

            if "security_plan" in needs:
                sec_text = f"《{name}》安保方案\n风险等级：一般\n负责人：安保部"
                sec_bytes = _make_pdf(f"《{name}》安保方案", sec_text)
                sec_path = f"activities/{activity.id}/{uuid4().hex}.pdf"
                await upload_file(sec_path, sec_bytes, "application/pdf")

                _add_doc(db, activity.id, security.id,
                         f"{name}_安保方案.pdf", sec_path,
                         len(sec_bytes), "application/pdf", ["安保"])

                risk = {"社区志愿服务日": "低", "职工运动会": "高"}.get(name, "一般")
                db.add(SecurityPlan(
                    activity_id=activity.id,
                    risk_level=risk,
                    audit_status="已审核",
                    manager_id=security.id,
                    sign_time=now,
                ))
                await db.flush()

            if "approval" in needs:
                approval_status = "approved"
                opinion = None
                if target == "待补充备案材料":
                    approval_status = "rectification"
                    opinion = "材料不完整，请补充活动预算明细和消防验收证明"
                elif target == "不通过/已终止":
                    approval_status = "rejected"
                    opinion = "活动方案不符合相关规定，不予批准"

                approval_path = None
                if approval_status == "approved":
                    appr_text = f"《{name}》政府批文\n经审核，该活动符合相关规定，批准举办。\n批准日期：{now.strftime('%Y-%m-%d')}"
                    appr_bytes = _make_pdf(f"《{name}》政府批文", appr_text)
                    approval_path = f"activities/{activity.id}/{uuid4().hex}.pdf"
                    await upload_file(approval_path, appr_bytes, "application/pdf")

                    _add_doc(db, activity.id, liaison.id,
                             f"{name}_政府批文.pdf", approval_path,
                             len(appr_bytes), "application/pdf", ["批文"])

                db.add(ApprovalRecord(
                    activity_id=activity.id,
                    liaison_id=liaison.id,
                    approval_status=approval_status,
                    attachment_url=approval_path,
                    approval_date=now if approval_status == "approved" else None,
                    rectification_opinion=opinion,
                ))
                await db.flush()

            # ── extra documents for variety ──
            if target in ("待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办",
                          "举办中", "已结束"):
                xlsx_rows = [
                    ["项目", "内容", "状态"],
                    ["场地审批", location, "已完成"],
                    ["消防验收", "合格", "已完成"],
                    ["安保人员", "已安排", "已完成"],
                ]
                xlsx_bytes = _make_xlsx(f"{name}备案材料清单", xlsx_rows)
                xlsx_path = f"activities/{activity.id}/{uuid4().hex}.xlsx"
                await upload_file(xlsx_path, xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                _add_doc(db, activity.id, promoter.id,
                         f"{name}_备案清单.xlsx", xlsx_path,
                         len(xlsx_bytes),
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         ["备案"])

            if target in ("审批通过", "审批通过-待举办", "举办中", "已结束"):
                csv_rows = [
                    ["时间", "事项", "负责人"],
                    ["筹备期", "场地布置", "行政部"],
                    ["活动当天", "现场安保", "安保部"],
                    ["活动结束", "场地清理", "行政部"],
                ]
                csv_bytes = _make_csv(csv_rows)
                csv_path = f"activities/{activity.id}/{uuid4().hex}.csv"
                await upload_file(csv_path, csv_bytes, "text/csv; charset=utf-8")
                _add_doc(db, activity.id, promoter.id,
                         f"{name}_工作安排.csv", csv_path,
                         len(csv_bytes), "text/csv; charset=utf-8", ["安排"])

            if target in ("审批通过-待举办", "举办中", "已结束"):
                docx_bytes = _make_docx(f"《{name}》安保责任书",
                    f"《{name}》安保责任书\n\n"
                    f"主办方：{sponsor}\n"
                    f"安保负责人：安保部\n"
                    f"已签署，责任明确。")
                docx_path = f"activities/{activity.id}/{uuid4().hex}.docx"
                await upload_file(docx_path, docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                _add_doc(db, activity.id, security.id,
                         f"{name}_安保责任书.docx", docx_path,
                         len(docx_bytes),
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         ["签署"])

            if target in ("举办中", "已结束"):
                jpg_bytes = _make_jpg()
                jpg_path = f"activities/{activity.id}/{uuid4().hex}.jpg"
                await upload_file(jpg_path, jpg_bytes, "image/jpeg")
                _add_doc(db, activity.id, promoter.id,
                         f"{name}_现场照片.jpg", jpg_path,
                         len(jpg_bytes), "image/jpeg", ["影像"])

            # ── set final status via transitions ──
            from app.services.workflow_service import WorkflowService
            wf = WorkflowService(db)

            PATH: dict[str, list[str]] = {
                "待设计方案":        [],
                "待安保方案设计":     ["待安保方案设计"],
                "待备案申请":        ["待安保方案设计", "待备案申请"],
                "备案材料已交接":     ["待安保方案设计", "待备案申请", "备案材料已交接"],
                "审批通过":          ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过"],
                "审批通过-待举办":    ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办"],
                "举办中":            ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办", "举办中"],
                "已结束":            ["待安保方案设计", "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办", "举办中", "已结束"],
                "待补充备案材料":     ["待安保方案设计", "待备案申请", "备案材料已交接", "待补充备案材料"],
                "不通过/已终止":      ["待安保方案设计", "待备案申请", "备案材料已交接", "不通过/已终止"],
                "已取消":            [],
                "已延期":            [],
            }

            path = PATH[target]
            for to_status in path:
                await wf.transition(activity.id, to_status, security)

            # ── FilingDoc for filing-ready activities ──
            if target in ("备案材料已交接", "审批通过", "审批通过-待举办",
                          "举办中", "已结束", "待补充备案材料", "不通过/已终止"):
                from app.models.filing import FilingDoc
                fd = FilingDoc(
                    activity_id=activity.id,
                    is_qualified=(target not in ("待补充备案材料", "不通过/已终止")),
                    generated_at=now,
                    handover_status="已交接" if target != "不通过/已终止" else None,
                )
                db.add(fd)

            # ── key_materials for security plan activities ──
            if "security_plan" in needs:
                from sqlalchemy import text as sa_text
                is_bad = (target == "待补充备案材料")
                materials = [
                    ("消防验收证明", True),
                    ("安全责任书", True),
                    ("场地审批表", True),
                    ("应急预案", not is_bad),
                ]
                if is_bad:
                    materials.append(("活动预算明细", False))
                pre_signed = target not in ("待备案申请", "待补充备案材料", "待安保方案设计")
                for mat_name, qualified in materials:
                    await db.execute(sa_text(
                        "INSERT INTO key_materials (name, is_qualified, sign_status) "
                        "VALUES (:n, :q, :s)"
                    ), {"n": mat_name, "q": qualified,
                        "s": "signed" if pre_signed else "unsigned"})
                    mat_result = await db.execute(sa_text(
                        "SELECT id FROM key_materials WHERE name=:n ORDER BY created_at DESC LIMIT 1"
                    ), {"n": mat_name})
                    mat_id = mat_result.scalar_one()
                    # link to security plan
                    sp_result = await db.execute(
                        select(SecurityPlan).where(SecurityPlan.activity_id == activity.id)
                    )
                    sp = sp_result.scalar_one()
                    await db.execute(sa_text(
                        "INSERT INTO security_plan_materials (security_plan_id, material_id) "
                        "VALUES (:sid, :mid) ON CONFLICT DO NOTHING"
                    ), {"sid": sp.id, "mid": mat_id})
                    # also link to filing doc if exists
                    if "approval" in needs and target not in ("不通过/已终止",):
                        fd_result = await db.execute(
                            select(FilingDoc).where(FilingDoc.activity_id == activity.id)
                        )
                        fd = fd_result.scalar_one_or_none()
                        if fd:
                            await db.execute(sa_text(
                                "INSERT INTO filing_doc_materials (filing_doc_id, material_id) "
                                "VALUES (:fid, :mid) ON CONFLICT DO NOTHING"
                            ), {"fid": fd.id, "mid": mat_id})

            # force-cancel / force-postpone
            if target in ("已取消", "已延期") and activity.status == "待设计方案":
                db.add(ActivityStatusLog(
                    activity_id=activity.id,
                    from_status="待设计方案",
                    to_status=target,
                    operator_id=security.id,
                    comment="测试强制变更",
                ))
                db.add(ImplementationRecord(
                    activity_id=activity.id,
                    admin_id=security.id,
                    change_status=target,
                    change_reason="测试强制变更",
                    archived_at=now,
                ))
                activity.status = target

            await db.commit()
            print(f"created: {name} → {target}")

    print("done")


def _add_doc(db, activity_id, uploader_id, filename, minio_path, file_size, content_type, tags=None):
    db.add(Document(
        activity_id=activity_id,
        uploader_id=uploader_id,
        filename=filename,
        minio_path=minio_path,
        file_size=file_size,
        content_type=content_type,
        tags=tags or [],
    ))


async def _ensure_user(db, username, email, role_names):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        return user
    role_result = await db.execute(select(Role).where(Role.name.in_(role_names)))
    roles = role_result.scalars().all()
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("pass123"),
        display_name=username,
    )
    db.add(user)
    await db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)
    return user


if __name__ == "__main__":
    asyncio.run(seed())
