"""创建预设测试活动，覆盖 12 种状态 + 附件 + FilledDocument + KeyMaterial。幂等。

活动主题：五大道景区。方案/安保场景多样化组合。
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text as sa_text

from app.auth import hash_password
from app.database import async_session
from app.models.activity import (
    Activity, ActivityPlan, ActivityStatusLog, ApprovalRecord,
    ImplementationRecord, SecurityPlan,
)
from app.models.document import Document
from app.models.material import KeyMaterial, SecurityPlanMaterial
from app.models.template import FilledDocument
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.services.minio_client import upload_file

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


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
        if y < 50: c.showPage(); y = 780
    c.save()
    return buf.getvalue()


def _make_xlsx(title: str, rows: list[list[str]]) -> bytes:
    import zipfile; from io import BytesIO
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'))
        zf.writestr("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'))
        zf.writestr("xl/workbook.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'))
        zf.writestr("xl/_rels/workbook.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'))
        rows_xml = "".join(
            "<row>" + "".join(f"<c t=\"inlineStr\"><is><t>{v}</t></is></c>" for v in row) + "</row>"
            for row in rows)
        zf.writestr("xl/worksheets/sheet1.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{rows_xml}</sheetData></worksheet>'))
    return buf.getvalue()


def _load_image(filename: str) -> bytes:
    """Load image from docs/ directory."""
    path = DOCS_DIR / filename
    if path.exists():
        return path.read_bytes()
    return b""


# ── scenarios ──

PLAN_SCENARIOS = [
    # (has_opening, has_performers, regular_crowd, opening_crowd, staff_count, contact_phone)
    # A: 大型（有开幕式+有演员嘉宾）
    ("是", "是", "3000-5000", "5000-10000", 30, "13800138001"),
    # B: 中型（有开幕式+无演员）
    ("是", "否", "1000-3000", "3000-5000", 20, "13800138002"),
    # C: 小型（无开幕式+无演员）
    ("否", "否", "1000以下", "", 10, "13800138003"),
]

SEC_SCENARIOS = [
    # (risk_level, security_staff_count)
    # 高
    ("高风险", 50),
    # 中
    ("中低风险", 25),
    # 低
    ("低风险", 10),
]

# ── activity definitions ──
# (name, type, location, sponsor, est_days, dl_days, target_status, created_days_ago)
ACTIVITIES = [
    # ── pending / in-progress (today) ──
    ("五大道海棠花节",       "民俗活动", "五大道景区", "和平区文旅局", 30, 20, "待设计方案",       0),
    ("民园广场音乐节",       "文艺汇演", "民园广场",   "市文旅局",     28, 18, "待设计方案",       0),
    ("先农大院文创市集",     "商贸活动", "先农大院",   "和平区商务局", 25, 15, "待安保方案设计",   0),
    ("庆王府非遗文化展",     "民俗活动", "庆王府",     "和平区文化馆", 22, 12, "待安保方案设计",   0),
    ("五大道国际摄影展",     "其他",     "民园广场",   "市摄影协会",   26, 16, "待安保方案设计",   0),
    ("五大道咖啡文化节",     "商贸活动", "五大道景区", "和平区商务局", 20, 10, "待备案申请",       0),
    ("民园广场消夏晚会",     "文艺汇演", "民园广场",   "和平区文旅局", 18,  9, "待备案申请",       0),
    ("五大道海棠花节春季场", "民俗活动", "五大道景区", "和平区文旅局", 21, 11, "待备案申请",       0),
    ("五大道音乐啤酒节",     "商贸活动", "民园广场",   "市文旅局",     15,  5, "备案材料已交接",   0),
    ("先农大院中秋灯会",     "民俗活动", "先农大院",   "和平区文旅局", 16,  6, "备案材料已交接",   0),
    ("五大道马拉松赛",       "体育赛事", "五大道景区", "市体育局",     14,  7, "审批通过",         0),
    ("民园广场健步走活动",   "体育赛事", "民园广场",   "和平区体育局", 10,  5, "审批通过-待举办",  0),
    ("五大道国际骑行节",     "体育赛事", "五大道景区", "市体育局",     11,  6, "审批通过-待举办",  0),
    # ── terminal / anomaly (today) ──
    ("五大道新春嘉年华",     "文艺汇演", "民园广场",   "和平区文旅局",  3,  1, "举办中",           0),
    ("五大道宪法宣传周",     "其他",     "五大道景区", "和平区司法局",  2,  1, "已结束",           0),
    ("五大道腊八节施粥",     "民俗活动", "庆王府",     "和平区文化馆",  1,  0, "已结束",           0),
    ("五大道年货大集",       "商贸活动", "五大道景区", "和平区商务局", 10,  5, "待补充备案材料",   0),
    ("五大道摇滚音乐节",     "文艺汇演", "民园广场",   "市文旅局",      8,  3, "不通过/已终止",    0),
    ("先农大院灯光秀",       "其他",     "先农大院",   "和平区文旅局",  9,  4, "不通过/已终止",    0),
    ("五大道街头篮球赛",     "体育赛事", "五大道景区", "市体育局",      9,  4, "已取消",           0),
    ("庆王府春节祈福活动",   "民族宗教活动", "庆王府", "市宗教局",     10,  5, "已取消",           0),
    ("五大道读书分享会",     "民俗活动", "先农大院",   "和平区文化馆", 12,  6, "已延期",           0),
    ("五大道创意设计周",     "商贸活动", "民园广场",   "市设计协会",   11,  5, "已延期",           0),
    # ── historical: 2026-05 (30-60 days ago) ──
    ("五大道五一花车巡游",   "文艺汇演", "五大道景区", "和平区文旅局", 35, 25, "已结束",           45),
    ("五大道春季招聘会",     "商贸活动", "民园广场",   "和平区人社局", 40, 30, "已结束",           50),
    ("五大道少儿艺术节",     "文艺汇演", "民园广场",   "和平区教育局", 38, 28, "已结束",           40),
    ("五大道星空音乐会",     "文艺汇演", "民园广场",   "市文旅局",     42, 32, "举办中",           35),
    ("五大道消防演习活动",   "其他",     "五大道景区", "和平区消防支队",36, 26, "审批通过-待举办", 55),
    ("五大道非遗技艺展",     "民俗活动", "庆王府",     "和平区文化馆", 44, 34, "审批通过",         60),
    ("五大道进口商品展销",   "商贸活动", "民园广场",   "市商务局",     35, 25, "备案材料已交接",   42),
    ("五大道端午祭孔大典",   "民族宗教活动", "庆王府", "市宗教局",     40, 30, "不通过/已终止",    38),
    ("五大道亲子嘉年华",     "民俗活动", "五大道景区", "和平区教育局", 32, 22, "已取消",           55),
    # ── historical: 2026-04 (60-90 days ago) ──
    ("五大道清明踏青活动",   "民俗活动", "五大道景区", "和平区文旅局", 65, 55, "已结束",           80),
    ("五大道樱花节",         "民俗活动", "五大道景区", "市文旅局",     70, 60, "已结束",           75),
    ("五大道全民健身日",     "体育赛事", "五大道景区", "市体育局",     68, 58, "已结束",           70),
    ("五大道知识产权周",     "其他",     "民园广场",   "市科技局",     62, 52, "审批通过-待举办", 85),
    ("五大道企业家沙龙",     "商贸活动", "庆王府",     "市工商联",     60, 50, "审批通过",         90),
    ("五大道开光祈福法会",   "民族宗教活动", "庆王府", "市宗教局",     66, 56, "不通过/已终止",    68),
    ("五大道春季长跑节",     "体育赛事", "五大道景区", "市体育局",     58, 48, "已取消",           72),
    ("五大道茶文化博览会",   "商贸活动", "先农大院",   "市茶协",       64, 54, "已延期",           78),
    # ── historical: 2026-03 (90-120 days ago) ──
    ("五大道妇女节表彰会",   "文艺汇演", "民园广场",   "和平区妇联",   95, 85, "已结束",          110),
    ("五大道消费者权益日",   "其他",     "五大道景区", "市市监局",    100, 90, "已结束",          100),
    ("五大道郁金香花展",     "民俗活动", "五大道景区", "市园林局",     98, 88, "已结束",           95),
    ("五大道科创企业路演",   "商贸活动", "民园广场",   "市科技局",     92, 82, "审批通过-待举办", 115),
    ("五大道新年祈福法会",   "民族宗教活动", "庆王府", "市宗教局",    105, 95, "不通过/已终止",   108),
    ("五大道元宵民俗庙会",   "民俗活动", "五大道景区", "市文旅局",    110,100, "已取消",          120),
]

STATUS_NEEDS = {
    "待设计方案":        [],
    "待安保方案设计":     ["plan_with_fd", "seed_materials"],
    "待备案申请":        ["plan_with_fd", "sec_with_fd_deferred", "materials_deferred", "seed_materials"],
    "备案材料已交接":     ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials"],
    "审批通过":          ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials", "approval"],
    "审批通过-待举办":    ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials", "approval"],
    "举办中":            ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials", "approval"],
    "已结束":            ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials", "approval"],
    "待补充备案材料":     ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials", "approval"],
    "不通过/已终止":      ["plan_with_fd", "sec_with_fd_signed", "materials_signed", "seed_materials", "approval"],
    "已取消":            ["plan_with_fd", "seed_materials"],
    "已延期":            ["plan_with_fd", "seed_materials"],
}

TEMPLATE_DISPLAY_NAMES = {
    "activity_plan": "活动方案",
    "security_plan": "安保方案",
    "risk_assessment": "风险评估报备表",
    "responsibility_letter": "安全消防责任确认书",
    "filing_commitment": "活动备案承诺书",
}

ALL_MATERIAL_TYPES = ["activity_plan", "security_plan", "risk_assessment", "responsibility_letter", "filing_commitment"]
DEFERRED_TYPES = ["security_plan", "risk_assessment", "responsibility_letter", "filing_commitment"]


def _build_plan_snapshot(scenario_idx: int, name: str, start: str, end: str) -> dict:
    """Build activity_plan data_snapshot from scenario."""
    s = PLAN_SCENARIOS[scenario_idx % len(PLAN_SCENARIOS)]
    has_opening, has_performers, regular_crowd, opening_crowd, staff_count, phone = s
    data = {
        "activity_content": f"《{name}》活动方案\n在五大道景区举办{name}，丰富市民文化生活。",
        "start_time": start,
        "end_time": end,
        "total_days": 1,
        "has_opening": has_opening,
        "has_performers": has_performers,
        "regular_crowd": regular_crowd,
        "construction_plan": f"舞台搭建方案：在指定区域搭建{ '开幕式' if has_opening == '是' else '' }活动舞台，配备灯光音响设备。",
        "contact_phone": phone,
        "remarks": "",
    }
    if has_opening == "是":
        data["opening_start"] = f"{start} 09:00"
        data["opening_end"] = f"{start} 10:00"
        data["opening_crowd"] = opening_crowd
    if has_performers == "是":
        data["performer_count"] = 20
        data["guest_count"] = 10
    return data


def _build_sec_snapshot(scenario_idx: int) -> dict:
    """Build security_plan data_snapshot from scenario."""
    risk, sec_count = SEC_SCENARIOS[scenario_idx % len(SEC_SCENARIOS)]
    data = {
        "security_staff_config": f"安保人员配置方案：共{sec_count}人，分3组轮班值守。\nA组负责入口安检，B组场内巡逻，C组应急待命。",
        "security_staff_count": sec_count,
        "movement_plan": "动线设计：主入口→安检区→活动区→应急出口。设置单向通道避免人流对冲。",
        "equipment_list": "安保设备清单：\n- 金属探测门 2台\n- 手持安检仪 4台\n- 对讲机 10部\n- 监控摄像头 8个",
        "emergency_plan": "应急预案：\n1. 突发事件立即启动应急响应\n2. 疏散引导员按预定路线引导人员撤离\n3. 医疗救护组第一时间到位\n4. 及时向公安机关报告",
    }
    if risk == "高风险":
        data["medical_plan"] = "医疗救护措施：设置医疗救护点1个，配备急救箱2套、AED除颤仪1台。联系120急救中心预留救护车。"
        data["fire_plan"] = "消防措施：配置灭火器12具、消防水带4条。开展消防演练，确保消防通道畅通。"
        data["crowd_control"] = "人流管控方案：设置入口计数系统，场内人数超过安全容量80%时启动限流。设置铁马隔离带分流。"
    elif risk == "中低风险":
        data["fire_plan"] = "消防措施：配置灭火器8具。检查消防设施，确保消防通道畅通。"
    return data


def _build_risk_snapshot(name: str, location: str, plan_s: int, sec_s: int) -> dict:
    """Build risk_assessment data_snapshot."""
    p = PLAN_SCENARIOS[plan_s % len(PLAN_SCENARIOS)]
    risk, _ = SEC_SCENARIOS[sec_s % len(SEC_SCENARIOS)]
    return {
        "reporting_unit": "天津市和平区文化和旅游局",
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "project_name": name,
        "activity_type": "民俗活动",
        "sponsor": "和平区文旅局",
        "organizer": "天津市演出公司",
        "participants": "市民、游客",
        "activity_start": (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d"),
        "activity_end": (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d"),
        "activity_location": location,
        "is_indoor": "户外",
        "location_type": "旅游景区",
        "activity_content": f"在{location}举办{name}",
        "crowd_scale": p[2],
        "staff_count": p[4],
        "security_count": SEC_SCENARIOS[sec_s % len(SEC_SCENARIOS)][1],
        "has_tickets": "否",
        "has_media": "是" if plan_s == 0 else "否",
        "media_channel": "直播" if plan_s == 0 else "",
        "media_name": "和平区融媒体中心" if plan_s == 0 else "",
        "media_type": "官方" if plan_s == 0 else "",
        "risk_factors": [
            "人群聚集可能引发拥挤踩踏风险",
            "活动现场临时用电存在安全隐患",
            "天气变化可能导致活动延期",
            "食品安全管理不善可能引发群体性事件",
        ],
        "mitigation_measures": [
            "制定详细人流管控方案，设置单向通道和限流措施",
            "聘请专业电工布线，配置漏电保护器",
            "制定恶劣天气应急预案，设置备用室内场地",
            "严格食品供应商资质审核，设置食品安全监督岗",
        ],
        "contact_person": "张三",
        "contact_phone": "13800138001",
        "assessor_signature": "signatures/sig1.jpg",
    }


def _build_resp_snapshot() -> dict:
    """Build responsibility_letter data_snapshot."""
    return {
        "sponsor_unit": "天津市和平区文化和旅游局",
        "security_leader_name": "李四",
        "security_leader_signature": "signatures/sig2.jpg",
        "confirm_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "confirm_location": "天津市和平区五大道景区",
    }


def _build_commitment_snapshot(activity, plan_s: int, sec_s: int) -> dict:
    """Build filing_commitment data_snapshot from activity and scenarios."""
    p = PLAN_SCENARIOS[plan_s % len(PLAN_SCENARIOS)]
    sec = SEC_SCENARIOS[sec_s % len(SEC_SCENARIOS)]
    return {
        "project_name": activity.name,
        "sponsor": activity.sponsor,
        "estimated_time": activity.estimated_time.strftime("%Y年%m月%d日") if activity.estimated_time else "",
        "location": activity.location,
        "activity_type": activity.type,
        "crowd_scale": p[2],
        "security_staff_count": str(sec[1]),
        "filing_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


# ── helpers ──

def _add_doc(db, activity_id, uploader_id, filename, minio_path, file_size, content_type, tags=None):
    db.add(Document(
        activity_id=activity_id, uploader_id=uploader_id,
        filename=filename, minio_path=minio_path,
        file_size=file_size, content_type=content_type, tags=tags or [],
    ))


async def _ensure_user(db, email, display_name, role_names, phone=""):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        if phone and not user.contact_phone:
            user.contact_phone = phone; await db.commit()
        return user
    role_result = await db.execute(select(Role).where(Role.name.in_(role_names)))
    roles = role_result.scalars().all()
    user = User(email=email, password_hash=hash_password("pass123"), display_name=display_name, contact_phone=phone)
    db.add(user); await db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit(); await db.refresh(user)
    return user


async def _create_km(db, activity_id: str, material_type: str) -> KeyMaterial:
    """Create or get KeyMaterial by (activity_id, material_type)."""
    result = await db.execute(
        select(KeyMaterial).where(
            KeyMaterial.activity_id == activity_id,
            KeyMaterial.material_type == material_type,
        )
    )
    km = result.scalar_one_or_none()
    if km:
        return km
    km = KeyMaterial(
        name=TEMPLATE_DISPLAY_NAMES.get(material_type, material_type),
        activity_id=activity_id,
        material_type=material_type,
    )
    db.add(km); await db.flush()
    return km


async def _create_fd(db, activity_id, template_type: str, data_snapshot: dict,
                      generated_by_id, version_number: int = 1,
                      minio_path: str | None = None) -> FilledDocument:
    """Create a FilledDocument record."""
    fd = FilledDocument(
        activity_id=activity_id,
        template_type=template_type,
        version_number=version_number,
        data_snapshot=data_snapshot,
        minio_path=minio_path,
        generated_by=generated_by_id,
    )
    db.add(fd); await db.flush()
    return fd


async def _link_sp_material(db, security_plan_id, material_id):
    """Link KeyMaterial to SecurityPlan."""
    await db.execute(sa_text(
        "INSERT INTO security_plan_materials (security_plan_id, material_id) "
        "VALUES (:sid, :mid) ON CONFLICT DO NOTHING"
    ), {"sid": security_plan_id, "mid": material_id})


# ── main seed ──

async def seed():
    async with async_session() as db:
        # ── ensure users ──
        promoter = await _ensure_user(db, "promoter@test.com", "promoter", ["Promoter"], "13900139001")
        security = await _ensure_user(db, "security@test.com", "security", ["SecurityOfficer"], "13900139002")
        security_mgr = await _ensure_user(db, "security_mgr@test.com", "security_mgr", ["SecurityManager"], "13900139003")
        liaison = await _ensure_user(db, "liaison@test.com", "liaison", ["GovLiaison"], "13900139004")

        # ── check existing ──
        names = [a[0] for a in ACTIVITIES]
        existing = await db.execute(select(Activity).where(Activity.name.in_(names)))
        if existing.scalars().all():
            print("skip: activities already seeded"); return

        now = datetime.now(timezone.utc)

        # ── upload signature & material images to MinIO ──
        SIG_PATHS: dict[int, str] = {}
        for idx in [1, 2, 3]:
            sig_bytes = _load_image(f"签名{idx}.jpg")
            if sig_bytes:
                sig_path = f"seed/signatures/sig{idx}.jpg"
                try:
                    await upload_file(sig_path, sig_bytes, "image/jpeg")
                    SIG_PATHS[idx] = sig_path
                    print(f"uploaded: 签名{idx}.jpg → {sig_path}")
                except Exception:
                    SIG_PATHS[idx] = sig_path

        MAT_PATHS: dict[int, str] = {}
        for idx in [1, 2, 3]:
            mat_bytes = _load_image(f"材料{idx}.jpg")
            if mat_bytes:
                mat_path = f"seed/materials/mat{idx}.jpg"
                try:
                    await upload_file(mat_path, mat_bytes, "image/jpeg")
                    MAT_PATHS[idx] = mat_path
                    print(f"uploaded: 材料{idx}.jpg → {mat_path}")
                except Exception:
                    MAT_PATHS[idx] = mat_path

        # ── create activities ──
        for i, row in enumerate(ACTIVITIES):
            name, atype, location, sponsor, est_days, dl_days, target = row[:7]
            created_days_ago = row[7] if len(row) > 7 else 0
            created_at = now - timedelta(days=created_days_ago)
            estimated = created_at + timedelta(days=est_days)
            deadline = created_at + timedelta(days=dl_days)

            plan_s = i % len(PLAN_SCENARIOS)
            sec_s = i % len(SEC_SCENARIOS)

            activity = Activity(
                name=name, type=atype, estimated_time=estimated,
                location=location, sponsor=sponsor,
                sponsor_contact="测试联系人", sponsor_phone="13800138000",
                deadline=deadline, status="待设计方案",
                owner_id=promoter.id, designer_id=promoter.id,
                created_at=created_at, updated_at=created_at,
            )
            db.add(activity); await db.flush()
            needs = STATUS_NEEDS.get(target, [])

            plan_start = estimated.strftime("%Y-%m-%d")
            plan_end = estimated.strftime("%Y-%m-%d")

            # ── plan_with_fd ──
            if "plan_with_fd" in needs:
                plan_data = _build_plan_snapshot(plan_s, name, plan_start, plan_end)
                plan_fd = await _create_fd(db, activity.id, "activity_plan", plan_data, promoter.id, 1)

                plan_pdf = _make_pdf(f"《{name}》活动方案", f"活动方案 v1\n{plan_data['activity_content']}")
                plan_pdf_path = f"filled_documents/{activity.id}/activity_plan/v1.pdf"
                await upload_file(plan_pdf_path, plan_pdf, "application/pdf")
                plan_fd.pdf_path = plan_pdf_path
                plan_fd.minio_path = plan_pdf_path  # activity_plan is NOT deferred

                plan_km = await _create_km(db, activity.id, "activity_plan")
                plan_km.current_filled_document_id = plan_fd.id
                plan_km.sign_status = "signed"
                plan_km.is_qualified = True

                ap_entity = ActivityPlan(
                    activity_id=activity.id,
                    content=plan_data["activity_content"],
                    attachment_url=plan_pdf_path,
                    submit_time=now,
                    designer_id=promoter.id,
                    is_overdue=False,
                    current_filled_document_id=plan_fd.id,
                    material_id=plan_km.id,
                )
                db.add(ap_entity)
                _add_doc(db, activity.id, promoter.id, f"{name}_活动方案.pdf",
                         plan_pdf_path, len(plan_pdf), "application/pdf", ["方案"])

            # ── sec_with_fd_deferred: SecurityPlan + deferred FilledDocuments ──
            if "sec_with_fd_deferred" in needs:
                sec_data = _build_sec_snapshot(sec_s)
                risk_level, _ = SEC_SCENARIOS[sec_s % len(SEC_SCENARIOS)]

                # create deferred FilledDocument (minio_path=NULL)
                sec_fd = await _create_fd(db, activity.id, "security_plan", sec_data, security.id, 1)

                # create security_plan entity
                sp = SecurityPlan(
                    activity_id=activity.id,
                    risk_level=risk_level,
                    audit_status="待签署",
                )
                db.add(sp); await db.flush()

                # KeyMaterial for security_plan
                sec_km = await _create_km(db, activity.id, "security_plan")
                sec_km.current_filled_document_id = sec_fd.id
                await _link_sp_material(db, sp.id, sec_km.id)

                # activity_plan km link (created in plan_with_fd)
                ap_km = await db.execute(
                    select(KeyMaterial).where(
                        KeyMaterial.activity_id == activity.id,
                        KeyMaterial.material_type == "activity_plan",
                    )
                )
                ap_km_row = ap_km.scalar_one_or_none()
                if ap_km_row:
                    await _link_sp_material(db, sp.id, ap_km_row.id)

            # ── materials_deferred: create KeyMaterial + deferred FilledDocument ──
            if "materials_deferred" in needs:
                sp_result = await db.execute(select(SecurityPlan).where(SecurityPlan.activity_id == activity.id))
                sp = sp_result.scalar_one()
                risk_level = sp.risk_level

                for mt in ["risk_assessment", "responsibility_letter", "filing_commitment"]:
                    if mt == "risk_assessment":
                        snap = _build_risk_snapshot(name, location, plan_s, sec_s)
                    elif mt == "responsibility_letter":
                        snap = _build_resp_snapshot()
                    else:
                        snap = _build_commitment_snapshot(activity, plan_s, sec_s)

                    fd = await _create_fd(db, activity.id, mt, snap, security.id, 1)  # deferred: minio_path=NULL
                    km = await _create_km(db, activity.id, mt)
                    km.current_filled_document_id = fd.id
                    await _link_sp_material(db, sp.id, km.id)

            # ── sec_with_fd_signed: SecurityPlan with generated DOCX + signature ──
            if "sec_with_fd_signed" in needs:
                sec_data = _build_sec_snapshot(sec_s)
                risk_level, _ = SEC_SCENARIOS[sec_s % len(SEC_SCENARIOS)]
                sig_idx = (i % 3) + 1
                sig_path = SIG_PATHS.get(sig_idx, "")

                # inject manager_signature
                sec_data["manager_signature"] = sig_path

                sec_fd = await _create_fd(db, activity.id, "security_plan", sec_data, security_mgr.id, 1)
                docx_path = f"filled_documents/{activity.id}/security_plan/v1.docx"
                sec_docx = _make_pdf(f"《{name}》安保方案",
                    f"安保方案 v1 (已签署)\n风险等级：{risk_level}\n负责人签名：已签")
                await upload_file(docx_path, sec_docx, "application/pdf")
                sec_fd.minio_path = docx_path

                sp = SecurityPlan(
                    activity_id=activity.id, risk_level=risk_level,
                    audit_status="已签署", manager_id=security_mgr.id, sign_time=now,
                )
                db.add(sp); await db.flush()

                sec_km = await _create_km(db, activity.id, "security_plan")
                sec_km.current_filled_document_id = sec_fd.id
                sec_km.sign_status = "signed"
                sec_km.is_qualified = True
                await _link_sp_material(db, sp.id, sec_km.id)

                # activity plan km link
                ap_km = await db.execute(
                    select(KeyMaterial).where(
                        KeyMaterial.activity_id == activity.id,
                        KeyMaterial.material_type == "activity_plan",
                    )
                )
                ap_km_row = ap_km.scalar_one_or_none()
                if ap_km_row:
                    ap_km_row.sign_status = "signed"
                    await _link_sp_material(db, sp.id, ap_km_row.id)

                # update ActivityPlan material_id
                ap_entity = await db.execute(
                    select(ActivityPlan).where(ActivityPlan.activity_id == activity.id)
                )
                ap = ap_entity.scalar_one_or_none()
                if ap and ap_km_row:
                    ap.material_id = ap_km_row.id

            # ── materials_signed: generate DOCXs for all deferred + sign them ──
            if "materials_signed" in needs:
                sp_result = await db.execute(select(SecurityPlan).where(SecurityPlan.activity_id == activity.id))
                sp = sp_result.scalar_one()
                risk_level = sp.risk_level
                sig_idx = (i % 3) + 1
                sig_path = SIG_PATHS.get(sig_idx, "")

                for mt in ["risk_assessment", "responsibility_letter", "filing_commitment"]:
                    if mt == "risk_assessment":
                        snap = _build_risk_snapshot(name, location, plan_s, sec_s)
                        snap["manager_signature"] = sig_path
                        snap["assessor_signature"] = sig_path
                    elif mt == "responsibility_letter":
                        snap = _build_resp_snapshot()
                        snap["manager_signature"] = sig_path
                        snap["security_leader_signature"] = sig_path
                    else:
                        snap = _build_commitment_snapshot(activity, plan_s, sec_s)
                        snap["manager_signature"] = sig_path

                    fd = await _create_fd(db, activity.id, mt, snap, security_mgr.id, 1)
                    docx_path = f"filled_documents/{activity.id}/{mt}/v1.docx"
                    docx = _make_pdf(f"{TEMPLATE_DISPLAY_NAMES[mt]} v1 (已签署)",
                                     f"已签署\n签名：已签")
                    await upload_file(docx_path, docx, "application/pdf")
                    fd.minio_path = docx_path

                    km = await _create_km(db, activity.id, mt)
                    km.current_filled_document_id = fd.id
                    km.sign_status = "signed"
                    km.is_qualified = True
                    await _link_sp_material(db, sp.id, km.id)

                # update SecurityPlan with material_id
                sp_km_result = await db.execute(
                    select(KeyMaterial).where(
                        KeyMaterial.activity_id == activity.id,
                        KeyMaterial.material_type == "security_plan",
                    )
                )
                sp_km = sp_km_result.scalar_one_or_none()
                if sp_km:
                    sp.material_id = sp_km.id

                # update activity_plan material_id
                ap_km = await db.execute(
                    select(KeyMaterial).where(
                        KeyMaterial.activity_id == activity.id,
                        KeyMaterial.material_type == "activity_plan",
                    )
                )
                ap_km_row = ap_km.scalar_one_or_none()
                if ap_km_row:
                    ap_km_row.sign_status = "signed"

            # ── seed_materials: 消防验收证明 + 应急预案 ──
            if "seed_materials" in needs and "security_plan" not in needs:
                # security_plan entity might exist from sec_with_fd_* — link seed materials to it
                sp_result = await db.execute(
                    select(SecurityPlan).where(SecurityPlan.activity_id == activity.id)
                )
                sp = sp_result.scalar_one_or_none()
            elif "seed_materials" in needs:
                sp_result = await db.execute(
                    select(SecurityPlan).where(SecurityPlan.activity_id == activity.id)
                )
                sp = sp_result.scalar_one()

            if "seed_materials" in needs and sp:
                pre_signed = target not in ("待备案申请", "待补充备案材料", "待安保方案设计")
                for mat_name in [("消防验收证明", True), ("应急预案", True)]:
                    mat_id_val = uuid4()
                    await db.execute(sa_text(
                        "INSERT INTO key_materials (id, name, is_qualified, sign_status, audit_round, activity_id) "
                        "VALUES (:id, :n, :q, :s, 0, :aid)"
                    ), {"id": mat_id_val, "n": mat_name[0], "q": mat_name[1],
                        "s": "signed" if pre_signed else "unsigned",
                        "aid": activity.id})
                    await _link_sp_material(db, sp.id, mat_id_val)

            # ── approval ──
            if "approval" in needs:
                approval_status = "approved"
                opinion = None
                if target == "待补充备案材料":
                    approval_status = "rectification"
                    opinion = "材料不完整，请补充消防验收证明"
                elif target == "不通过/已终止":
                    approval_status = "rejected"
                    opinion = "活动方案不符合相关规定，不予批准"

                approval_path = None
                if approval_status == "approved" and MAT_PATHS:
                    mat_idx = (i % 3) + 1
                    approval_path = MAT_PATHS.get(mat_idx)

                db.add(ApprovalRecord(
                    activity_id=activity.id, liaison_id=liaison.id,
                    approval_status=approval_status,
                    attachment_url=approval_path,
                    approval_date=now if approval_status == "approved" else None,
                    rectification_opinion=opinion,
                ))
                await db.flush()

            # ── extra documents ──
            if target in ("待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办", "举办中", "已结束"):
                xlsx_rows = [["项目", "内容", "状态"],
                             ["场地审批", location, "已完成"],
                             ["消防验收", "合格", "已完成"],
                             ["安保人员", "已安排", "已完成"]]
                xlsx_bytes = _make_xlsx(f"{name}备案材料清单", xlsx_rows)
                xlsx_path = f"activities/{activity.id}/{uuid4().hex}.xlsx"
                await upload_file(xlsx_path, xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                _add_doc(db, activity.id, promoter.id,
                         f"{name}_备案清单.xlsx", xlsx_path, len(xlsx_bytes),
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ["备案"])

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
                await wf.transition(activity.id, to_status, security_mgr)

            # ── FilingDoc ──
            if target in ("备案材料已交接", "审批通过", "审批通过-待举办", "举办中", "已结束",
                          "待补充备案材料", "不通过/已终止"):
                from app.models.filing import FilingDoc
                db.add(FilingDoc(
                    activity_id=activity.id,
                    is_qualified=(target not in ("待补充备案材料", "不通过/已终止")),
                    generated_at=now,
                    handover_status="已交接" if target != "不通过/已终止" else None,
                ))

            # ── force-cancel / force-postpone ──
            if target in ("已取消", "已延期") and activity.status == "待设计方案":
                db.add(ActivityStatusLog(
                    activity_id=activity.id, from_status="待设计方案",
                    to_status=target, operator_id=security_mgr.id,
                    comment="测试强制变更"))
                db.add(ImplementationRecord(
                    activity_id=activity.id, admin_id=security_mgr.id,
                    change_status=target, change_reason="测试强制变更",
                    archived_at=now))
                activity.status = target

            await db.commit()
            print(f"created: {name} → {target} (plan_s={plan_s} sec_s={sec_s})")

    print("done")


if __name__ == "__main__":
    asyncio.run(seed())
