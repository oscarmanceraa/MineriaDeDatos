import unittest

from app import create_app
from app.etapa5.q4_urbano_rural import q4_datos
from app.modelo_estrella import consultar_vista, obtener_modelo


class ModeloEstrellaTests(unittest.TestCase):
    def test_load_matches_treated_source(self):
        summary = obtener_modelo()["summary"]

        self.assertEqual(summary["records"], 20087)
        self.assertEqual(summary["quantity"], 20087)
        self.assertEqual(summary["threatened"], 174)
        self.assertEqual(summary["risk"], 330)
        self.assertTrue(summary["all_valid"])
        self.assertTrue(all(check["ok"] for check in summary["validation"]))

    def test_drill_down_and_dice_reaggregate(self):
        default = consultar_vista("q1-concentracion-territorial", {})
        detailed = consultar_vista(
            "q1-concentracion-territorial",
            {
                "row_level": "municipio",
                "column_level": "clase",
                "f_anio": "2025",
                "f_fuente": "Todas",
            },
        )

        self.assertEqual(default["row_label"], "Provincia")
        self.assertEqual(detailed["row_label"], "Municipio")
        self.assertEqual(detailed["column_label"], "Clase")
        self.assertLess(detailed["summary"]["records"], default["summary"]["records"])

    def test_pivot_preserves_aggregates_and_swaps_axes(self):
        ordinary = consultar_vista("q2-amenaza-taxon-fuente", {})
        pivoted = consultar_vista(
            "q2-amenaza-taxon-fuente",
            {"pivot": "1"},
        )

        self.assertEqual(ordinary["summary"], pivoted["summary"])
        self.assertEqual(ordinary["row_label"], pivoted["column_label"])
        self.assertEqual(ordinary["column_label"], pivoted["row_label"])

    def test_temporal_insight_compares_equivalent_months(self):
        result = consultar_vista("q3-crecimiento-temporal", {})
        comparison = result["period_comparison"]
        first = comparison["periods"][2024]["records"]
        second = comparison["periods"][2025]["records"]

        self.assertGreater(first, 0)
        self.assertGreater(second, 0)
        self.assertAlmostEqual(
            comparison["change_pct"],
            100 * (second - first) / first,
        )
        self.assertIn("enero–agosto", result["insights"][1]["question"])

    def test_q4_route_uses_local_model_and_filters_bubble_chart(self):
        client = create_app().test_client()
        response = client.get(
            "/etapa-5/q4-urbano-rural-amenaza?"
            "provincia=Guavio&periodo=2024-2025&categoria=Rural"
        )
        body = response.get_data(as_text=True)
        default = q4_datos()
        filtered = q4_datos(
            provincia="Guavio",
            periodo="2024-2025",
            categoria="Rural",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("q4-barras", body)
        self.assertIn("q4-burbuja", body)
        self.assertNotIn("No se pudo consultar", body)
        self.assertEqual(len(filtered["chart_burbuja"]["puntos"]), 1)
        self.assertLess(
            int(filtered["indicadores"][1]["valor"]),
            int(default["indicadores"][1]["valor"]),
        )

    def test_all_questions_render_and_reject_invalid_levels(self):
        client = create_app().test_client()
        slugs = [
            "q1-concentracion-territorial",
            "q2-amenaza-taxon-fuente",
            "q3-crecimiento-temporal",
            "q4-urbano-rural-amenaza",
        ]

        for slug in slugs:
            response = client.get(f"/etapa-5/{slug}")
            self.assertEqual(response.status_code, 200, slug)
            body = response.get_data(as_text=True)
            if slug == "q4-urbano-rural-amenaza":
                self.assertEqual(body.count('class="q5-knowledge"'), 2)
            else:
                self.assertEqual(
                    body.count("Conocimiento multidimensional 0"),
                    2,
                    slug,
                )

        self.assertEqual(
            client.get(
                "/etapa-5/q1-concentracion-territorial?row_level=desconocido"
            ).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
