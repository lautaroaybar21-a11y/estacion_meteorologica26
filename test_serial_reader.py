import unittest

from serial_reader import parse_reading_line, soil_humidity_percent


class SoilHumidityTests(unittest.TestCase):
    def test_calibration_endpoints(self):
        self.assertEqual(soil_humidity_percent(1023), 0.0)
        self.assertEqual(soil_humidity_percent(300), 100.0)

    def test_value_is_clamped_to_calibrated_range(self):
        self.assertEqual(soil_humidity_percent(0), 100.0)

    def test_rejects_raw_value_outside_adc_range(self):
        with self.assertRaises(ValueError):
            soil_humidity_percent(1024)


class SerialParsingTests(unittest.TestCase):
    def test_parses_a_complete_reading(self):
        pending = {}
        lines = [
            "-- NUEVA LECTURA ---",
            "Fecha: 2026-10-27 Hora: 13:59:17",
            "Temperatura BMP: 22.46 C",
            "Presion: 1020.04 hPa",
            "Temperatura DHT: 21.20 C",
            "Humedad del aire: 65.00 %",
            "Humedad suelo RAW: 1022",
        ]

        reading = None
        for line in lines:
            result = parse_reading_line(line, pending)
            if result:
                reading = result

        self.assertIsNotNone(reading)
        self.assertEqual(reading["temperatura_bmp"], 22.46)
        self.assertEqual(reading["temperatura_dht"], 21.2)
        self.assertEqual(reading["presion_hpa"], 1020.04)
        self.assertEqual(reading["humedad_aire"], 65.0)
        self.assertEqual(reading["humedad_suelo_raw"], 1022)
        self.assertAlmostEqual(reading["humedad_suelo_pct"], 0.14)
        self.assertEqual(pending, {})

    def test_new_reading_marker_discards_incomplete_previous_data(self):
        pending = {"temperatura_bmp": 10.0}
        self.assertIsNone(parse_reading_line("-- NUEVA LECTURA ---", pending))
        self.assertEqual(pending, {})


if __name__ == "__main__":
    unittest.main()
