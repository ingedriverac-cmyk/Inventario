import sqlite3
import os
from datetime import datetime
import pandas as pd

class ControlInventario:
    def __init__(self, db_name="inventario.db"):
        self.db_name = db_name
        self.inicializar_db()

    def conectar(self):
        return sqlite3.connect(self.db_name)

    def inicializar_db(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    codigo TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    stock INTEGER NOT NULL,
                    stock_minimo INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_producto TEXT NOT NULL,
                    tipo_movimiento TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    fecha_hora TEXT NOT NULL,
                    FOREIGN KEY(codigo_producto) REFERENCES productos(codigo)
                )
            """)
            conn.commit()

    def registrar_producto(self, codigo, nombre, stock_inicial, stock_minimo):
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO productos VALUES (?, ?, ?, ?)", 
                               (codigo, nombre, stock_inicial, stock_minimo))
                
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO historial (codigo_producto, tipo_movimiento, cantidad2, fecha_hora)
                    VALUES (?, ?, ?, ?)
                """, (codigo, "STOCK INICIAL", stock_inicial, fecha_actual))
                
                conn.commit()
                print(f"\n✅ Éxito: Producto '{nombre}' registrado correctamente.")
        except sqlite3.IntegrityError:
            print(f"\n❌ Error: El código '{codigo}' ya existe en el sistema.")

    def registrar_entrada(self, codigo, cantidad):
        if cantidad <= 0:
            print("\n❌ Error: La cantidad debe ser mayor a cero.")
            return

        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE productos SET stock = stock + ? WHERE codigo = ?", (cantidad, codigo))
            
            if cursor.rowcount > 0:
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO historial (codigo_producto, tipo_movimiento, cantidad, fecha_hora)
                    VALUES (?, ?, ?, ?)
                """, (codigo, "ENTRADA", cantidad, fecha_actual))
                
                conn.commit()
                print(f"\n📥 Reabastecimiento: Añadidas {cantidad} unidades al producto '{codigo}'.")
            else:
                print("\n❌ Error: Producto no encontrado.")

    def registrar_salida(self, codigo, cantidad):
        if cantidad <= 0:
            print("\n❌ Error: La cantidad debe ser mayor a cero.")
            return

        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, stock, stock_minimo FROM productos WHERE codigo = ?", (codigo,))
            producto = cursor.fetchone()

            if not producto:
                print("\n❌ Error: Producto no encontrado.")
                return

            nombre, stock_actual, stock_minimo = producto

            if cantidad > stock_actual:
                print(f"\n❌ Venta rechazada: Stock insuficiente de '{nombre}'. Solo quedan {stock_actual} unidades.")
            else:
                nuevo_stock = stock_actual - cantidad
                cursor.execute("UPDATE productos SET stock = ? WHERE codigo = ?", (nuevo_stock, codigo))
                
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO historial (codigo_producto, tipo_movimiento, cantidad, fecha_hora)
                    VALUES (?, ?, ?, ?)
                """, (codigo, "SALIDA", cantidad, fecha_actual))
                
                conn.commit()
                print(f"\n📤 Venta exitosa: {cantidad} unidades retiradas de '{nombre}'.")
                
                if nuevo_stock <= stock_minimo:
                    print(f"⚠️  ALERTA: ¡El producto '{nombre}' llegó o bajó de su stock mínimo ({stock_minimo})! Stock actual: {nuevo_stock}")

    def mostrar_inventario(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos")
            productos = cursor.fetchall()

            if not productos:
                print("\n📭 El inventario está completamente vacío.")
                return

            self._imprimir_tabla_productos(productos)

    def buscar_producto(self, termino):
        """NUEVO MÉTODO: Busca productos por aproximación de nombre o código exacto."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            # El operador LIKE permite buscar coincidencias parciales
            cursor.execute("""
                SELECT * FROM productos 
                WHERE codigo = ? OR nombre LIKE ?
            """, (termino.upper(), f"%{termino}%"))
            resultados = cursor.fetchall()

            if not resultados:
                print(f"\n🔍 No se encontraron productos que coincidan con: '{termino}'")
                return

            print(f"\n🔍 Resultados de la búsqueda para '{termino}':")
            self._imprimir_tabla_productos(resultados)

    def editar_producto(self, codigo, nuevo_nombre, nuevo_minimo):
        """NUEVO MÉTODO: Modifica los parámetros de un producto sin alterar su stock."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE productos 
                SET nombre = ?, stock_minimo = ? 
                WHERE codigo = ?
            """, (nuevo_nombre, nuevo_minimo, codigo.upper()))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"\n✅ Éxito: Producto '{codigo}' actualizado correctamente.")
            else:
                print("\n❌ Error: No se encontró ningún producto con ese código.")

    def eliminar_producto(self, codigo):
        """NUEVO MÉTODO: Elimina físicamente un producto del catálogo."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            # Primero borramos su historial para no romper las restricciones de clave foránea
            cursor.execute("DELETE FROM historial WHERE codigo_producto = ?", (codigo.upper(),))
            cursor.execute("DELETE FROM productos WHERE codigo = ?", (codigo.upper(),))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"\n🗑️  Éxito: El producto '{codigo}' ha sido eliminado del sistema.")
            else:
                print("\n❌ Error: No se encontró ningún producto con ese código.")

    def exportar_a_excel(self, nombre_archivo="reporte_inventario.xlsx"):
        try:
            with self.conectar() as conn:
                query = """
                    SELECT h.id AS [ID Movimiento], 
                           h.codigo_producto AS [Código Producto], 
                           p.nombre AS [Nombre Producto], 
                           h.tipo_movimiento AS [Tipo de Movimiento], 
                           h.cantidad AS [Cantidad], 
                           h.fecha_hora AS [Fecha / Hora]
                    FROM historial h
                    LEFT JOIN productos p ON h.codigo_producto = p.codigo
                    ORDER BY h.id DESC
                """
                df = pd.read_sql_query(query, conn)
                if df.empty:
                    print("\n📭 No hay datos en el historial para exportar.")
                    return
                df.to_excel(nombre_archivo, index=False, sheet_name="Historial")
                print(f"\n📊 ¡Reporte exportado con éxito! Guardado como: '{nombre_archivo}'")
        except Exception as e:
            print(f"\n❌ Error al exportar a Excel: {e}")

    def mostrar_historial(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.id, h.codigo_producto, p.nombre, h.tipo_movimiento, h.cantidad, h.fecha_hora 
                FROM historial h
                LEFT JOIN productos p ON h.codigo_producto = p.codigo
                ORDER BY h.id DESC
            """)
            movimientos = cursor.fetchall()

            if not movimientos:
                print("\n📭 No hay movimientos registrados en el historial.")
                return

            print("\n" + "="*80)
            print(f"{'ID':<5} | {'CÓDIGO':<8} | {'PRODUCTO':<20} | {'TIPO':<15} | {'CANT':<6} | {'FECHA / HORA':<20}")
            print("="*80)
            for mov in movimientos:
                nombre_prod = mov[2] if mov[2] else "[Eliminado]"
                print(f"{mov[0]:<5} | {mov[1]:<8} | {nombre_prod:<20} | {mov[3]:<15} | {mov[4]:<6} | {mov[5]:<20}")
            print("="*80)

    def _imprimir_tabla_productos(self, lista_productos):
        """Método auxiliar interno para dar formato a los listados de productos."""
        print("\n" + "="*60)
        print(f"{'CÓDIGO':<10} | {'PRODUCTO':<20} | {'STOCK ACTUAL':<12} | {'STOCK MÍN':<10}")
        print("="*60)
        for prod in lista_productos:
            alerta = "⚠️ " if prod[2] <= prod[3] else "  "
            print(f"{prod[0]:<10} | {prod[1]:<20} | {prod[2]:<12} {alerta}| {prod[3]:<10}")
        print("="*60)

# --- LÓGICA DEL MENÚ INTERACTIVO ---

# --- LÓGICA DEL MENÚ INTERACTIVO ---

def ejecutar_menu():
    sistema = ControlInventario()
    
    while True:
        print("\n📦 --- SISTEMA DE CONTROL DE INVENTARIOS --- 📦")
        print("1. Ver Inventario Completo")
        print("2. Registrar Nuevo Producto")
        print("3. Registrar Entrada (Compra/Abastecer)")
        print("4. Registrar Salida (Venta/Retiro)")
        print("5. Buscar Producto 🔍")
        print("6. Editar Producto ✏️")
        print("7. Eliminar Producto 🗑️")
        print("8. Ver Historial de Movimientos 📜")
        print("9. Exportar Historial a Excel 📊")
        print("10. Salir")
        
        opcion = input("\nSeleccione una opción (1-10): ").strip()

        if opcion == "1":
            sistema.mostrar_inventario()
        elif opcion == "2":
            print("\n--- Registrar Nuevo Producto ---")
            codigo = input("Código del producto: ").strip().upper()
            nombre = input("Nombre del producto: ").strip()
            try:
                stock = int(input("Stock inicial: "))
                minimo = int(input("Stock mínimo de alerta: "))
                sistema.registrar_producto(codigo, nombre, stock, minimo)
            except ValueError:
                print("\n❌ Error: El stock y el mínimo deben ser números enteros.")
        elif opcion == "3":
            print("\n--- Registrar Entrada de Stock ---")
            codigo = input("Código del producto: ").strip().upper()
            try:
                cantidad = int(input("Cantidad a añadir: "))
                sistema.registrar_entrada(codigo, cantidad)
            except ValueError:
                print("\n❌ Error: La cantidad debe ser un número entero.")
        elif opcion == "4":
            print("\n--- Registrar Salida de Stock ---")
            codigo = input("Código del producto: ").strip().upper()
            try:
                cantidad = int(input("Cantidad a retirar: "))
                sistema.registrar_salida(codigo, cantidad)
            except ValueError:
                print("\n❌ Error: La cantidad debe ser un número entero.")
        elif opcion == "5":
            print("\n--- Buscar Producto ---")
            termino = input("Escriba el código o parte del nombre a buscar: ").strip()
            if termino:
                sistema.buscar_producto(termino)
            else:
                print("\n❌ Error: El término de búsqueda no puede estar vacío.")
        elif opcion == "6":
            print("\n--- Editar Producto ---")
            codigo = input("Código del producto que desea editar: ").strip().upper()
            nuevo_nombre = input("Nuevo nombre del producto: ").strip()
            try:
                nuevo_minimo = int(input("Nuevo stock mínimo de alerta: "))
                if nuevo_nombre:
                    sistema.editar_producto(codigo, nuevo_nombre, nuevo_minimo)
                else:
                    print("\n❌ Error: El nombre no puede quedar vacío.")
            except ValueError:
                print("\n❌ Error: El stock mínimo debe ser un número entero.")
        elif opcion == "7":
            print("\n--- Eliminar Producto ---")
            codigo = input("⚠️ ADVERTENCIA: Se borrará también su historial.\nCódigo del producto a eliminar: ").strip().upper()
            confirmacion = input(f"¿Está seguro de eliminar el producto {codigo}? (S/N): ").strip().upper()
            if confirmacion == "S":
                sistema.eliminar_producto(codigo)
            else:
                print("\n❌ Operación cancelada.")
        elif opcion == "8":
            sistema.mostrar_historial()
        elif opcion == "9":
            sistema.exportar_a_excel()
        elif opcion == "10":
            print("\n👋 ¡Gracias por usar el sistema de inventarios! Saliendo...")
            break
        else:
            print("\n❌ Opción inválida. Por favor, digite un número del 1 al 10.")
            
        input("\nPresione Enter para continuar...")
        os.system('cls' if os.name == 'nt' else 'clear')

# Forzamos el arranque directo del menú al ejecutar el archivo
ejecutar_menu()
