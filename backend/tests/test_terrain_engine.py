import unittest

from terrain_engine import FrontierGrid


class FrontierGridTests(unittest.TestCase):
    def test_same_seed_and_coordinate_produce_same_tile(self):
        first = FrontierGrid(1701).tile_at(22, 31)
        second = FrontierGrid(1701).tile_at(22, 31)

        self.assertEqual(first, second)
        self.assertEqual((22, 31), first.position)

    def test_grid_rejects_coordinates_outside_the_bounded_frontier(self):
        grid = FrontierGrid(1701)

        with self.assertRaises(ValueError):
            grid.tile_at(64, 0)

    def test_route_stays_in_bounds_and_avoids_impassable_tiles(self):
        grid = FrontierGrid(1701)
        known = {(x, y) for x in range(6, 15) for y in range(6, 15)}
        modifications = {
            "10,10": {"passable": False},
            "10,11": {"passable": False},
        }

        result = grid.find_route((8, 9), (12, 12), known=known, modifications=modifications)

        self.assertTrue(result.reached)
        self.assertEqual((8, 9), result.path[0])
        self.assertEqual((12, 12), result.path[-1])
        self.assertNotIn((10, 10), result.path)
        self.assertNotIn((10, 11), result.path)
        self.assertTrue(all(0 <= x < 64 and 0 <= y < 64 for x, y in result.path))

    def test_route_cannot_use_unknown_tiles_as_a_shortcut(self):
        grid = FrontierGrid(1701)
        known = {(8, 9), (9, 9), (10, 9)}

        result = grid.find_route((8, 9), (10, 10), known=known, modifications={})

        self.assertFalse(result.reached)
        self.assertEqual(((8, 9),), result.path)
        self.assertEqual("destination_unknown", result.reason)


if __name__ == "__main__":
    unittest.main()
