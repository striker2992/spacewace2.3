from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.contenedores.models import Contenedor, Servicio
from apps.cotizaciones.models import Cotizacion, CotizacionItem, CotizacionServicio
from apps.vendedores.models import Vendedor

User = get_user_model()


class Command(BaseCommand):
    help = "Carga datos de demostración (solo para desarrollo)."

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin1234")
            self.stdout.write("Usuario admin / admin1234 creado (cámbialo).")

        vendedores = []
        for username, nombre in [("ana", "Ana Pérez"), ("luis", "Luis Soto"), ("marta", "Marta Rojas")]:
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={"first_name": nombre.split()[0], "last_name": nombre.split()[1]},
            )
            if creado:
                user.set_password("demo1234")
                user.save()
            
            vendedor, _ = Vendedor.objects.get_or_create(
                user=user,
                defaults={"codigo": f"VEND-{username.upper()}"}
            )
            vendedores.append(vendedor)

        admin_user = User.objects.get(username="admin")
        Vendedor.objects.get_or_create(
            user=admin_user,
            defaults={"codigo": "VEND-ADMIN"}
        )

        # Cliente de la tienda
        comprador, creado = User.objects.get_or_create(
            username="cliente",
            defaults={"first_name": "Camila", "last_name": "Fuentes", "email": "camila@ejemplo.cl"},
        )
        if creado:
            comprador.set_password("demo1234")
            comprador.save()
            Cliente.objects.create(
                usuario=comprador, nombre="Camila Fuentes", rut="12.345.678-5",
                razon_social="Fuentes y Cía.", email=comprador.email,
                telefono="+56 9 5555 0101", direccion="Av. Costanera 1234, Coronel",
            )
            self.stdout.write("Cliente de tienda camila@ejemplo.cl / demo1234 creado.")

        if Contenedor.objects.exists():
            self.stdout.write("Ya hay datos; no se cargó nada más.")
            return

        catalogo = [
            ("Contenedor 20' estándar", "20DC", "nuevo", 4200, 15, "Coronel"),
            ("Contenedor 20' estándar", "20DC", "usado", 2600, 22, "San Antonio"),
            ("Contenedor 40' estándar", "40DC", "nuevo", 6100, 10, "Coronel"),
            ("Contenedor 40' High Cube", "40HC", "nuevo", 6900, 8, "Valparaíso"),
            ("Contenedor 40' refrigerado", "40RF", "usado", 14500, 3, "San Antonio"),
            ("Contenedor 20' Open Top", "20OT", "nuevo", 5400, 4, "Coronel"),
            ("Contenedor oficina 20'", "20OF", "nuevo", 9800, 2, "Coronel"),
        ]
        medidas = {
            "20DC": "Medidas internas: 5,90 x 2,35 x 2,39 m\nCapacidad: 33 m³\nCarga máxima: 28.000 kg",
            "40DC": "Medidas internas: 12,03 x 2,35 x 2,39 m\nCapacidad: 67 m³\nCarga máxima: 26.500 kg",
            "40HC": "Medidas internas: 12,03 x 2,35 x 2,69 m\nCapacidad: 76 m³\nCarga máxima: 26.500 kg",
            "40RF": "Medidas internas: 11,58 x 2,29 x 2,25 m\nTemperatura: -25 °C a +25 °C\nCarga máxima: 27.000 kg",
            "20OT": "Medidas internas: 5,90 x 2,35 x 2,34 m\nTecho removible con lona\nCarga máxima: 28.000 kg",
            "20OF": "Medidas internas: 5,90 x 2,35 x 2,39 m\nAislación térmica, ventana y puerta peatonal\nInstalación eléctrica básica",
        }
        contenedores = [
            Contenedor.objects.create(
                nombre=n, tipo=t, condicion=c, precio=p, stock=s, ubicacion=u,
                descripcion=f"{n} en condición {c}, listo para entrega en {u}.",
                especificaciones=medidas[t],
            )
            for n, t, c, p, s, u in catalogo
        ]
        # Algunos con otra disponibilidad, para ver los estados en el catálogo
        contenedores[2].estado = Contenedor.Estado.ARRENDADO
        contenedores[4].estado = Contenedor.Estado.MANTENIMIENTO
        for c in (contenedores[2], contenedores[4]):
            c.save(update_fields=["estado"])

        nombres = [
            "Agencia Alpha", "Construcciones S.A.", "Mercado Central", "Taller Mecánico",
            "Retail Sur", "Alimentos P&R", "Servicios Globales", "Alimentos Elementos",
        ]
        clientes = [
            Cliente.objects.create(
                nombre=n, email=f"contacto{i}@ejemplo.cl", telefono=f"+56 9 5555 00{i:02d}"
            )
            for i, n in enumerate(nombres, start=1)
        ]

        servicios = [
            Servicio.objects.create(nombre=n, descripcion=d, precio=p, unidad=u)
            for n, d, p, u in [
                ("Transporte y entrega", "Traslado en camión pluma hasta la dirección del cliente.", 1200, "km"),
                ("Instalación y nivelación", "Posicionamiento y nivelación del contenedor en terreno.", 3500, "servicio"),
                ("Modificación: ventana o puerta", "Corte e instalación de ventana o puerta peatonal.", 2800, "unidad"),
                ("Mantenimiento preventivo", "Revisión de estructura, sellos y pintura.", 1900, "visita"),
            ]
        ]

        hoy = timezone.localdate()
        estados_cot = ["aprobada", "pendiente", "rechazada", "pendiente", "aprobada", "pendiente"]
        for i, estado in enumerate(estados_cot):
            cot = Cotizacion.objects.create(
                cliente=clientes[i % len(clientes)],
                vendedor=vendedores[i % len(vendedores)],
                estado=estado,
                fecha=hoy - timedelta(days=i),
            )
            cont = contenedores[i % len(contenedores)]
            CotizacionItem.objects.create(
                cotizacion=cot, contenedor=cont, cantidad=1 + i % 3, precio_unitario=cont.precio
            )
            if i % 2 == 0:
                serv = servicios[i % len(servicios)]
                CotizacionServicio.objects.create(
                    cotizacion=cot, servicio=serv, cantidad=1, precio_unitario=serv.precio
                )

        # Una solicitud hecha por la clienta de la tienda, esperando valorización
        camila = Cliente.objects.filter(usuario__username="cliente").first()
        if camila:
            sol = Cotizacion.objects.create(
                cliente=camila, estado=Cotizacion.Estado.SOLICITADA, origen=Cotizacion.Origen.WEB,
                fecha_requerida=hoy + timedelta(days=20), direccion_entrega=camila.direccion,
                notas="Lo necesito como bodega para una obra.",
            )
            CotizacionItem.objects.create(
                cotizacion=sol, contenedor=contenedores[0], cantidad=2, precio_unitario=contenedores[0].precio
            )
            CotizacionServicio.objects.create(
                cotizacion=sol, servicio=servicios[0], cantidad=25, precio_unitario=servicios[0].precio
            )

        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))