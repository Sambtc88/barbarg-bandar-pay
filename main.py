import flet as ft
import datetime

def main(page: ft.Page):
    page.title = "واریزی باربرگ بندر"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # اطلاعات کارت‌ها و مدیر
    CARD_MEHR = "6063731055328091"
    CARD_SAMAN = "6219861986589132"
    MANAGER_PHONE = "09175766737"
    
    # روزشمار (مثال: ۲۸ روز باقی‌مانده از ۳۰ روز)
    days_left = 28

    # کنترلوندهای فرم ثبت واریز
    name_input = ft.TextField(label="نام و نام خانوادگی پرداخت‌کننده", border_radius=8)
    card_input = ft.TextField(label="شماره کارت پرداخت‌کننده (یا ۴ رقم آخر)", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
    selected_card_text = ft.Text("", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
    
    current_target_card = [""]

    def select_card(card_name, card_num):
        current_target_card[0] = f"{card_name} ({card_num})"
        selected_card_text.value = f"کارت مقصد انتخاب شده:\n{card_name}\n{card_num}"
        page.update()

    # دیالوگ (پنجره) فرم واریز
    form_dlg = ft.AlertDialog(
        title=ft.Text("ثبت اطلاعات واریزی", weight=ft.FontWeight.BOLD),
        content=ft.Column([
            selected_card_text,
            ft.Divider(),
            name_input,
            card_input,
            ft.ElevatedButton("انتخاب تصویر رسید از گالری", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: print("انتخاب عکس")),
        ], tight=True, spacing=15),
        actions=[
            ft.TextButton("انصراف", on_click=lambda _: close_dlg()),
            ft.ElevatedButton("ثبت نهایی و ارسال به مدیر", bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=lambda _: submit_payment())
        ]
    )

    def open_form(card_name, card_num):
        select_card(card_name, card_num);
        page.open(form_dlg)

    def close_dlg():
        form_dlg.open = False
        page.update()

    def submit_payment():
        if not name_input.value or not card_input.value:
            page.open(ft.SnackBar(ft.Text("لطفاً فیلدها را به طور کامل پر کنید!")))
            page.update()
            return
        
        # شبیه‌سازی ارسال اطلاعات و پیامک به مدیر (09175766737)
        print(f"ارسال پیامک و گزارش به مدیر به شماره {MANAGER_PHONE}...")
        print(f"پرداخت کننده: {name_input.value} | کارت مقصد: {current_target_card[0]}")
        
        close_dlg()
        page.open(ft.SnackBar(ft.Text("اطلاعات با موفقیت ثبت و پیامک برای مدیر ارسال شد! ✅")))
        page.update()

    # ظاهر صفحه اصلی اپلیکیشن
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("🚚 واریزی باربرگ بندر", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_900),
                ft.Divider(),
                
                # باکس روزشمار ۳۰ روزه
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.TIMER, color=ft.Colors.GREEN_800), ft.Text("روزشمار اشتراک ۳۰ روزه", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Text(f"{days_left} روز باقی‌مانده تا پایان دوره", size=16, color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15,
                    bgcolor=ft.Colors.GREEN_50,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.GREEN_300),
                    width=320
                ),
                
                ft.VerticalDivider(height=10),
                ft.Text("لطفاً کارت مقصد را برای واریز انتخاب کنید:", weight=ft.FontWeight.BOLD),
                
                # دکمه بانک مهر ایران
                ft.ElevatedButton(
                    content=ft.Column([
                        ft.Text("بانک مهر ایران", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(CARD_MEHR, size=13, color=ft.Colors.WHITE70, letterSpacing=1)
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
                    bgcolor=ft.Colors.GREEN_700,
                    style=ft.ButtonStyle(padding=15),
                    on_click=lambda _: open_form("بانک مهر ایران", CARD_MEHR),
                    width=320
                ),
                
                # دکمه بلو کارت سامان
                ft.ElevatedButton(
                    content=ft.Column([
                        ft.Text("بلو کارت سامان", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(CARD_SAMAN, size=13, color=ft.Colors.WHITE70, letterSpacing=1)
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
                    bgcolor=ft.Colors.BLUE_700,
                    style=ft.ButtonStyle(padding=15),
                    on_click=lambda _: open_form("بلو کارت سامان", CARD_SAMAN),
                    width=320
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            padding=20,
            alignment=ft.alignment.center
        )
    )

ft.app(target=main)
