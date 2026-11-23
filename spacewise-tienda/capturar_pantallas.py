"""Script para capturar pantallazos de SpaceWise usando Playwright."""
import os
import sys
import asyncio

# Ajustar el path del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_sqlite")

SCREENSHOT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BASE_URL = "http://127.0.0.1:8765"


async def capturar():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await page.goto(f"{BASE_URL}/catalogo/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC03_catalogo_publico.png"), full_page=False)
        print("✓ UC03_catalogo_publico.png")

        # Detalle de contenedor
        links = await page.query_selector_all("a[href*='/catalogo/']")
        for link in links:
            href = await link.get_attribute("href")
            if href and href != "/catalogo/" and "/catalogo/" in href:
                await link.click()
                await page.wait_for_load_state("networkidle")
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC03_detalle_contenedor.png"), full_page=False)
                print("✓ UC03_detalle_contenedor.png")
                break

        # Registro
        await page.goto(f"{BASE_URL}/accounts/registro/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC12_registro.png"), full_page=False)
        print("✓ UC12_registro.png")

        # Login
        await page.goto(f"{BASE_URL}/accounts/login/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC12_login.png"), full_page=False)
        print("✓ UC12_login.png")

        # Olvidé contraseña
        await page.goto(f"{BASE_URL}/accounts/clave/olvide/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC11_olvide_clave.png"), full_page=False)
        print("✓ UC11_olvide_clave.png")

        # --- PARTE 2: Cliente (camila@ejemplo.cl / demo1234) ---
        await page.goto(f"{BASE_URL}/accounts/login/")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[name="username"]', 'camila@ejemplo.cl')
        await page.fill('input[name="password"]', 'demo1234')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        # Catálogo como cliente
        await page.goto(f"{BASE_URL}/catalogo/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC07_catalogo_cliente.png"), full_page=False)
        print("✓ UC07_catalogo_cliente.png")

        # Agregar al carrito
        forms = await page.query_selector_all("form[action*='/carrito/agregar/']")
        if forms:
            btn = await forms[0].query_selector("button[type='submit']")
            if btn:
                await btn.click()
                await page.wait_for_load_state("networkidle")

        await page.goto(f"{BASE_URL}/carrito/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC07_carrito.png"), full_page=False)
        print("✓ UC07_carrito.png")

        # Solicitar cotización
        await page.goto(f"{BASE_URL}/cotizaciones/solicitar/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC04_solicitar_cotizacion.png"), full_page=False)
        print("✓ UC04_solicitar_cotizacion.png")

        # Mis cotizaciones
        await page.goto(f"{BASE_URL}/cotizaciones/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC04_mis_cotizaciones.png"), full_page=False)
        print("✓ UC04_mis_cotizaciones.png")

        # Mis pedidos
        await page.goto(f"{BASE_URL}/pedidos/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC07_mis_pedidos.png"), full_page=False)
        print("✓ UC07_mis_pedidos.png")

        # Mis garantías
        await page.goto(f"{BASE_URL}/garantias/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC08_mis_garantias.png"), full_page=False)
        print("✓ UC08_mis_garantias.png")

        # Perfil
        await page.goto(f"{BASE_URL}/accounts/perfil/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC01_perfil_cliente.png"), full_page=False)
        print("✓ UC01_perfil_cliente.png")

        # Logout usando nuevo context o limpiando cookies
        await context.clear_cookies()

        # --- PARTE 3: Admin (admin / admin1234) ---
        await page.goto(f"{BASE_URL}/accounts/login/")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'admin1234')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        # Dashboard
        await page.goto(f"{BASE_URL}/panel/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC09_dashboard.png"), full_page=False)
        print("✓ UC09_dashboard.png")

        # Gestión de contenedores
        await page.goto(f"{BASE_URL}/panel/contenedores/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC03_gestion_contenedores.png"), full_page=False)
        print("✓ UC03_gestion_contenedores.png")

        # Servicios
        await page.goto(f"{BASE_URL}/panel/contenedores/servicios/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC03_gestion_servicios.png"), full_page=False)
        print("✓ UC03_gestion_servicios.png")

        # Clientes
        await page.goto(f"{BASE_URL}/panel/clientes/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC02_gestion_clientes.png"), full_page=False)
        print("✓ UC02_gestion_clientes.png")

        # Detalle de cliente
        links = await page.query_selector_all("a[href*='/panel/clientes/']")
        for link in links:
            href = await link.get_attribute("href")
            if href and href != "/panel/clientes/" and "/panel/clientes/" in href and "nuevo" not in href:
                await link.click()
                await page.wait_for_load_state("networkidle")
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC02_detalle_cliente.png"), full_page=False)
                print("✓ UC02_detalle_cliente.png")
                break

        # Bandeja de cotizaciones
        await page.goto(f"{BASE_URL}/panel/cotizaciones/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC04_bandeja_cotizaciones.png"), full_page=False)
        print("✓ UC04_bandeja_cotizaciones.png")

        # Detalle de cotización
        links = await page.query_selector_all("a[href*='/panel/cotizaciones/']")
        for link in links:
            href = await link.get_attribute("href")
            if href and href != "/panel/cotizaciones/" and "nueva" not in href and href.rstrip("/").split("/")[-1].isdigit():
                await link.click()
                await page.wait_for_load_state("networkidle")
                await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC04_detalle_cotizacion.png"), full_page=True)
                print("✓ UC04_detalle_cotizacion.png")
                break

        # Gestión de pedidos
        await page.goto(f"{BASE_URL}/panel/pedidos/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC07_gestion_pedidos.png"), full_page=False)
        print("✓ UC07_gestion_pedidos.png")

        # Bandeja de garantías
        await page.goto(f"{BASE_URL}/panel/garantias/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC08_bandeja_garantias.png"), full_page=False)
        print("✓ UC08_bandeja_garantias.png")

        # Reportes
        await page.goto(f"{BASE_URL}/panel/reportes/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC10_reportes.png"), full_page=True)
        print("✓ UC10_reportes.png")

        # Cuentas bloqueadas
        await page.goto(f"{BASE_URL}/panel/cuentas-bloqueadas/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC11_cuentas_bloqueadas.png"), full_page=False)
        print("✓ UC11_cuentas_bloqueadas.png")

        # Perfil admin
        await page.goto(f"{BASE_URL}/accounts/perfil/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC01_perfil_admin.png"), full_page=False)
        print("✓ UC01_perfil_admin.png")

        # Nuevo contenedor (formulario)
        await page.goto(f"{BASE_URL}/panel/contenedores/nuevo/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC03_nuevo_contenedor.png"), full_page=False)
        print("✓ UC03_nuevo_contenedor.png")

        # Nueva cotización (formulario)
        await page.goto(f"{BASE_URL}/panel/cotizaciones/nueva/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "UC04_nueva_cotizacion.png"), full_page=False)
        print("✓ UC04_nueva_cotizacion.png")

        await browser.close()
        print(f"\n=== Todas las capturas guardadas en {SCREENSHOT_DIR} ===")


asyncio.run(capturar())
