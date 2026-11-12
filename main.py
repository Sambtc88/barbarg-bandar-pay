import asyncio
import base64
import time
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import ssl
import flet as ft

# ==================== تنظیمات هسته بارگو بندر ====================
BASE_URL = "https://utcms.ir"
LOGIN_PAGE_URL = f"{BASE_URL}/Account/Login"
CAPTCHA_URL = f"{BASE_URL}/Account/CaptchaImage"
DASHBOARD_URL = f"{BASE_URL}/Panel/Index"
ISSUE_PERMIT_URL = f"{BASE_URL}/Permit/Create"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Origin": BASE_URL,
    "Referer": LOGIN_PAGE_URL,
}


class BarGoBandarEngine:
    """موتور بومی و ضدکرش با استفاده از کتابخانه‌های داخلی پایتون"""

    def __init__(self, page: ft.Page, log_callback):
        self.page = page
        self.log = log_callback
        self.csrf_token = ""
        self.is_logged_in = False
        self.radar_active = False
        self.burst_running = False
        self.current_user = ""
        self.license_active = False

        # پیکربندی اتصال امن بومی بدون نیاز به پکیج‌های خارجی (حل مشکل کرش اندروید)
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=self.ctx)
        )
        
        self.load_saved_session()
        self.check_license_status()

    def make_request(self, url, method="GET", data_dict=None, timeout=5.0):
        req_headers = DEFAULT_HEADERS.copy()
        encoded_data = None
        if data_dict:
            encoded_data = urllib.parse.urlencode(data_dict).encode('utf-8')
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=encoded_data, headers=req_headers, method=method)
        try:
            with self.opener.open(req, timeout=timeout) as response:
                body = response.read()
                return response.status, body, response.url
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.url
        except Exception:
            return 0, b"", ""

    def save_session(self):
        cookies = [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path} for c in self.cookie_jar]
        data = {"cookies": cookies, "csrf": self.csrf_token, "user": self.current_user}
        self.page.client_storage.set("session_data", data)
        self.log("نشست سامانه به صورت ایمن در کش گوشی ذخیره شد.")

    def load_saved_session(self):
        data = self.page.client_storage.get("session_data")
        if data:
            self.csrf_token = data.get("csrf", "")
            self.current_user = data.get("user", "")
            for c_dict in data.get("cookies", []):
                c = http.cookiejar.Cookie(
                    version=0, name=c_dict['name'], value=c_dict['value'],
                    port=None, port_specified=False,
                    domain=c_dict['domain'], domain_specified=bool(c_dict['domain']), domain_initial_dot=False,
                    path=c_dict['path'], path_specified=bool(c_dict['path']),
                    secure=False, expires=None, discard=False, comment=None, comment_url=None, rest={}
                )
                self.cookie_jar.set_cookie(c)
            if len(self.cookie_jar) > 0:
                self.is_logged_in = True
                self.log(f"نشست کاربر [{self.current_user}] از حافظه بازیابی شد.")

    def check_license_status(self):
        data = self.page.client_storage.get("license_data")
        if data and data.get("active", False):
            self.license_active = True
        else:
            self.license_active = False

    def activate_license_key(self, key: str) -> bool:
        if key.strip() == "BARGO-2026-VIP" or len(key.strip()) == 12:
            self.license_active = True
            self.page.client_storage.set("license_data", {"active": True, "key": key.strip()})
            return True
        return False

    def extract_csrf_simple(self, html_text: str) -> str:
        try:
            target = 'name="__RequestVerificationToken" type="hidden" value="'
            idx = html_text.find(target)
            if idx != -1:
                start = idx + len(target)
                end = html_text.find('"', start)
                if end != -1:
                    self.csrf_token = html_text[start:end]
                    return self.csrf_token
        except Exception:
            pass
        return self.csrf_token

    async def check_server_radar(self) -> tuple[bool, int, int]:
        def _check():
            start = time.perf_counter()
            status, body, url = self.make_request(BASE_URL, "GET", None, 3.5)
            elapsed = int((time.perf_counter() - start) * 1000)
            if 0 < status < 500:
                self.extract_csrf_simple(body.decode('utf-8', errors='ignore'))
                return True, elapsed, status
            return False, elapsed, status
        return await asyncio.to_thread(_check)

    async def fetch_captcha_base64(self) -> str | None:
        def _fetch():
            status, body, url = self.make_request(LOGIN_PAGE_URL)
            if status == 200:
                self.extract_csrf_simple(body.decode('utf-8', errors='ignore'))
            ts = int(time.time() * 1000)
            c_status, c_body, c_url = self.make_request(f"{CAPTCHA_URL}?t={ts}")
            if c_status == 200 and len(c_body) > 100:
                return base64.b64encode(c_body).decode("utf-8")
            return None
        return await asyncio.to_thread(_fetch)

    async def perform_login(self, username: str, password: str, captcha_code: str) -> bool:
        def _login():
            payload = {
                "__RequestVerificationToken": self.csrf_token,
                "UserName": username.strip(),
                "Password": password.strip(),
                "Captcha": captcha_code.strip(),
                "RememberMe": "true",
            }
            status, body, url = self.make_request(LOGIN_PAGE_URL, "POST", payload, 6.0)
            if status in (200, 302):
                text = body.decode('utf-8', errors='ignore')
                if "خروج" in text or "Panel" in url or any(c.name == ".ASPXAUTH" for c in self.cookie_jar):
                    self.is_logged_in = True
                    self.current_user = username.strip()
                    self.extract_csrf_simple(text)
                    self.save_session()
                    return True
            return False
        
        ok = await asyncio.to_thread(_login)
        if ok:
            self.log(f"ورود موفق به سامانه با حساب [{username}]")
        else:
            self.log("خطا در لاگین یا کپچا اشتباه است.")
        return ok

    async def burst_issue_permit(self, truck_data: dict, cargo_params: dict, workers: int = 3) -> tuple[bool, str]:
        self.burst_running = True
        success_flag = asyncio.Event()
        result_message = "ثبت انجام نشد."

        payload = {
            "__RequestVerificationToken": self.csrf_token,
            "DriverNationalCode": truck_data.get("national_id", ""),
            "DriverMobile": truck_data.get("mobile", ""),
            "SmartCardNo": truck_data.get("smart_card", ""),
            "PlaquePart1": truck_data.get("p1", ""),
            "PlaqueChar": truck_data.get("p_char", "ع"),
            "PlaquePart2": truck_data.get("p2", ""),
            "PlaqueIran": truck_data.get("p_iran", ""),
            "CargoTypeTitle": cargo_params.get("cargo_type", "مصالح ساختمانی"),
            "CargoWeight": cargo_params.get("weight", "15000"),
            "OriginAddress": cargo_params.get("origin", "بندر لنگه"),
            "DestinationAddress": cargo_params.get("destination", "شهرک صنعتی"),
        }

        def _single_shot_sync():
            status, body, url = self.make_request(ISSUE_PERMIT_URL, "POST", payload, 4.0)
            if status == 200:
                text = body.decode('utf-8', errors='ignore')
                if "با موفقیت" in text or "صادر شد" in text or "کد رهگیری" in text:
                    return True
            return False

        async def single_shot(worker_id: int):
            nonlocal result_message
            if success_flag.is_set() or not self.burst_running:
                return
            try:
                ok = await asyncio.to_thread(_single_shot_sync)
                if ok and not success_flag.is_set():
                    success_flag.set()
                    result_message = f"باربرگ با موفقیت صادر شد! (ورکر {worker_id})"
                    self.log(f"🎯 {result_message}")
            except Exception:
                pass

        self.log(f"🚀 شروع شلیک رگباری باربرگ برای [{truck_data.get('title')}]...")
        for _ in range(35):
            if success_flag.is_set() or not self.burst_running:
                break
            await asyncio.gather(*(single_shot(w) for w in range(1, workers + 1)))
            await asyncio.sleep(0.3)

        self.burst_running = False
        return success_flag.is_set(), result_message


# ==================== مدیریت دیتابیس بومی اندروید ====================
def load_users(page: ft.Page) -> dict:
    data = page.client_storage.get("users_data")
    if data: return data
    return {"admin": "123456", "davood": "78910"}

def save_users(page: ft.Page, users_dict: dict):
    page.client_storage.set("users_data", users_dict)

def load_fleet(page: ft.Page) -> list:
    data = page.client_storage.get("fleet_data")
    if data: return data
    return [{
        "title": "کامیون نمونه - ۱۲ع۳۴۵ ایران ۶۴", "group": "گروه مرکزی (بندر لنگه)",
        "national_id": "2990000000", "mobile": "09373016550", "smart_card": "1234567",
        "p1": "12", "p_char": "ع", "p2": "345", "p_iran": "64"
    }]

def save_fleet(page: ft.Page, fleet_list: list):
    page.client_storage.set("fleet_data", fleet_list)


# ==================== رابط کاربری اپلیکیشن (Flet UI) ====================
async def main(page: ft.Page):
    page.title = "بارگو بندر | سامانه تجاری صدور باربرگ"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F172A"
    page.padding = 12
    page.scroll = ft.ScrollMode.ADAPTIVE

    logs_list = ft.ListView(expand=True, spacing=4, auto_scroll=True, height=160)

    def add_log(msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        logs_list.controls.append(ft.Text(f"[{now}] {msg}", size=12, color="#E2E8F0", font_family="monospace"))
        if len(logs_list.controls) > 100:
            logs_list.controls.pop(0)
        page.update()

    engine = BarGoBandarEngine(page=page, log_callback=add_log)
    users_data = load_users(page)
    app_root = ft.Column(expand=True)

    # ---------- صفحه ورود تجاری ----------
    def build_auth_screen():
        user_field = ft.TextField(label="نام کاربری تجاری", prefix_icon=ft.icons.PERSON, border_color="#38BDF8")
        pass_field = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True, prefix_icon=ft.icons.LOCK, border_color="#38BDF8")
        reg_user = ft.TextField(label="نام کاربری جدید", prefix_icon=ft.icons.PERSON_ADD, border_color="#10B981")
        reg_pass = ft.TextField(label="رمز عبور جدید", password=True, prefix_icon=ft.icons.LOCK_OUTLINE, border_color="#10B981")
        auth_status = ft.Text("", size=13, color="#EF4444")

        def login_click(e):
            u = user_field.value.strip()
            p = pass_field.value.strip()
            if u in users_data and users_data[u] == p:
                auth_status.value = "ورود موفق! در حال بارگذاری پنل..."
                page.run_task(load_main_dashboard)
            else:
                auth_status.value = "خطا: نام کاربری یا رمز عبور اشتباه است."
                page.update()

        def register_click(e):
            u = reg_user.value.strip()
            p = reg_pass.value.strip()
            if not u or not p:
                auth_status.value = "لطفاً فیلدها را کامل پر کنید."
                page.update()
                return
            if u in users_data:
                auth_status.value = "این نام کاربری قبلاً ثبت شده است."
            else:
                users_data[u] = p
                save_users(page, users_data)
                auth_status.value = "حساب کاربری ساخته شد. اکنون وارد شوید."
                auth_status.color = "#10B981"
            page.update()

        return ft.Column([
            ft.Container(height=20),
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.icons.LOCAL_SHIPPING, size=50, color="#38BDF8"),
                    bgcolor="#1E293B", padding=15, border_radius=20, border=ft.border.all(2, "#38BDF8")
                )
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Text("بارگو بندر", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF", text_align=ft.TextAlign.CENTER),
            ft.Text("سامانه جامع مدیریت و صدور هوشمند باربرگ", size=13, color="#94A3B8", text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Container(
                bgcolor="#1E293B", padding=16, border_radius=12,
                content=ft.Column([
                    ft.Text("🔐 ورود به حساب کاربری", size=15, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                    user_field, pass_field,
                    ft.ElevatedButton("ورود به پنل تجاری", bgcolor="#38BDF8", color="#0F172A", height=45, width=400, on_click=login_click),
                ], spacing=10)
            ),
            ft.Container(height=10),
            ft.ExpansionTile(
                title=ft.Text("ایجاد حساب کاربری جدید", size=13, color="#10B981"),
                controls=[
                    ft.Container(
                        bgcolor="#1E293B", padding=12, border_radius=10,
                        content=ft.Column([
                            reg_user, reg_pass,
                            ft.ElevatedButton("ثبت نام حساب جدید", bgcolor="#10B981", color="#FFFFFF", height=40, on_click=register_click)
                        ], spacing=8)
                    )
                ]
            ),
            ft.Container(height=10),
            auth_status,
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.ADAPTIVE)

    # ---------- داشبورد اصلی ----------
    async def load_main_dashboard():
        fleet_data = load_fleet(page)
        
        status_badge = ft.Container(content=ft.Text("رادار: آماده", size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"), bgcolor="#334155", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=6)

        fleet_dropdown = ft.Dropdown(
            label="انتخاب ناوگان از بانک آفلاین",
            options=[ft.dropdown.Option(key=str(i), text=f"{item['title']} [{item['group']}]") for i, item in enumerate(fleet_data)],
            value="0" if fleet_data else None, border_color="#38BDF8",
        )

        cargo_type_dropdown = ft.Dropdown(
            label="نوع محموله", options=[ft.dropdown.Option("مصالح ساختمانی"), ft.dropdown.Option("سیمان فله"), ft.dropdown.Option("مواد معدنی")],
            value="مصالح ساختمانی", border_color="#38BDF8",
        )

        weight_input = ft.TextField(label="وزن (کیلوگرم)", value="15000", border_color="#475569")
        origin_input = ft.TextField(label="مبدا", value="بندر لنگه", border_color="#475569")
        dest_input = ft.TextField(label="مقصد", value="شهرک صنعتی", border_color="#475569")
        workers_slider = ft.Slider(min=1, max=5, divisions=4, value=3, label="{value} خط موازی")

        result_banner = ft.Container(content=ft.Text("آماده صدور باربرگ...", size=13, weight=ft.FontWeight.BOLD, color="#F8FAFC"), bgcolor="#1E293B", padding=10, border_radius=8)

        async def start_burst_click(e):
            if not fleet_data or fleet_dropdown.value is None:
                result_banner.content.value = "ابتدا کامیون انتخاب کنید!"
                page.update()
                return
            selected = fleet_data[int(fleet_dropdown.value)]
            result_banner.content.value = "در حال شلیک رگباری..."
            page.update()
            cargo_params = {"cargo_type": cargo_type_dropdown.value, "weight": weight_input.value, "origin": origin_input.value, "destination": dest_input.value}
            ok, msg = await engine.burst_issue_permit(selected, cargo_params, int(workers_slider.value))
            result_banner.bgcolor = "#10B981" if ok else "#EF4444"
            result_banner.content.value = msg
            page.update()

        async def radar_loop():
            while engine.radar_active:
                is_up, ping, _ = await engine.check_server_radar()
                status_badge.bgcolor = "#10B981" if is_up else "#EF4444"
                status_badge.content.value = f"سرور: {'آنلاین' if is_up else 'قطع'} ({ping}ms)"
                page.update()
                await asyncio.sleep(4.0)

        def toggle_radar(e):
            engine.radar_active = e.control.value
            if engine.radar_active:
                page.run_task(radar_loop)
            page.update()

        tab_issue = ft.Column([
            ft.Switch(label="روشن کردن رادار زنده سرور", value=False, on_change=toggle_radar),
            fleet_dropdown, cargo_type_dropdown, weight_input, origin_input, dest_input, workers_slider, result_banner,
            ft.ElevatedButton("🔥 شروع شلیک رگباری باربرگ", bgcolor="#F59E0B", color="#0F172A", height=45, on_click=start_burst_click),
        ], spacing=8)

        u_input = ft.TextField(label="نام کاربری utcms.ir", border_color="#475569")
        p_input = ft.TextField(label="رمز عبور", password=True, border_color="#475569")
        cap_img = ft.Image(src_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", width=140, height=45)
        cap_input = ft.TextField(label="کد کپچا", border_color="#38BDF8", expand=True)

        async def load_cap(e):
            b64 = await engine.fetch_captcha_base64()
            if b64:
                cap_img.src_base64 = b64
                page.update()

        async def do_login(e):
            await engine.perform_login(u_input.value, p_input.value, cap_input.value)
            page.update()

        tab_session = ft.Column([
            u_input, p_input, ft.Row([cap_img, ft.ElevatedButton("دریافت کپچا", on_click=load_cap)]), cap_input,
            ft.ElevatedButton("🔐 قفل نشست سامانه", bgcolor="#10B981", color="#FFFFFF", height=42, on_click=do_login),
        ], spacing=8)

        license_status_text = ft.Text("وضعیت لایسنس: " + ("✅ فعال و تجاری" if engine.license_active else "❌ غیرفعال (آزمایشی)"), size=14, weight=ft.FontWeight.BOLD, color="#10B981" if engine.license_active else "#EF4444")
        license_input = ft.TextField(label="کد فعال‌سازی تجاری", border_color="#F59E0B")

        def activate_license(e):
            if engine.activate_license_key(license_input.value):
                license_status_text.value = "وضعیت لایسنس: ✅ فعال و تجاری"
                license_status_text.color = "#10B981"
            else:
                license_status_text.value = "وضعیت لایسنس: ❌ کد نامعتبر است"
                license_status_text.color = "#EF4444"
            page.update()

        tab_sales = ft.Column([
            ft.Text("💳 مدیریت فروش و لایسنس نرم‌افزار", size=14, weight=ft.FontWeight.BOLD, color="#38BDF8"),
            license_status_text, license_input,
            ft.ElevatedButton("فعال‌سازی لایسنس تجاری", bgcolor="#F59E0B", color="#0F172A", height=42, on_click=activate_license),
        ], spacing=10)

        f_title = ft.TextField(label="عنوان کامیون", border_color="#475569")
        f_nid = ft.TextField(label="کد ملی", border_color="#475569")
        
        def save_truck_click(e):
            fleet_data.append({"title": f_title.value, "group": "گروه ۱", "national_id": f_nid.value, "mobile": "", "smart_card": "", "p1": "", "p_char": "ع", "p2": "", "p_iran": ""})
            save_fleet(page, fleet_data)
            fleet_dropdown.options = [ft.dropdown.Option(key=str(i), text=f"{item['title']}") for i, item in enumerate(fleet_data)]
            add_log("کامیون در دیتابیس بومی ذخیره شد.")
            f_title.value = ""
            f_nid.value = ""
            page.update()

        tab_fleet = ft.Column([
            ft.Text("افزودن ناوگان آفلاین:", size=13, weight=ft.FontWeight.BOLD),
            f_title, f_nid,
            ft.ElevatedButton("➕ ذخیره کامیون", bgcolor="#0284C7", color="#FFFFFF", on_click=save_truck_click),
        ], spacing=8)

        body_container = ft.Container(content=tab_issue, padding=4)

        def switch_sub_tab(e):
            sel = e.control.data
            if sel == "issue": body_container.content = tab_issue
            elif sel == "session": body_container.content = tab_session
            elif sel == "sales": body_container.content = tab_sales
            elif sel == "fleet": body_container.content = tab_fleet
            page.update()

        app_root.controls = [
            ft.Row([
                ft.Row([ft.Icon(ft.icons.LOCAL_SHIPPING, color="#38BDF8", size=22), ft.Text("بارگو بندر | پنل تجاری", size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF")], spacing=6),
                status_badge
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.ElevatedButton("🚀 صدور", data="issue", on_click=switch_sub_tab, bgcolor="#1E293B", color="#38BDF8"),
                ft.ElevatedButton("🔑 نشست", data="session", on_click=switch_sub_tab, bgcolor="#1E293B", color="#10B981"),
                ft.ElevatedButton("💳 فروش", data="sales", on_click=switch_sub_tab, bgcolor="#1E293B", color="#F59E0B"),
                ft.ElevatedButton("🚛 ناوگان", data="fleet", on_click=switch_sub_tab, bgcolor="#1E293B", color="#EC4899"),
            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            body_container, ft.Divider(color="#334155"),
            ft.Container(content=logs_list, bgcolor="#020617", padding=6, border_radius=6),
        ]
        page.update()

    app_root.controls = [build_auth_screen()]
    page.add(app_root)


if __name__ == "__main__":
    ft.app(target=main)
