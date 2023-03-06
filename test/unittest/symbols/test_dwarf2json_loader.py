import unittest
from unittest.mock import patch, mock_open, MagicMock

from monk.symbols.dwarf2json_loader import Dwarf2JsonLoader
from monk.symbols.types import types

class TestDwarf2jsonLoader(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data="""
        {
            "base_types":{
                "int":{
                    "size":4
                }
            },
            "k1":"val1",
            "k2":{
                "k3":"val2"
            }
        }"""
        )
    def test_constructor(self, mock_file):
        d = Dwarf2JsonLoader("test/path")
        mock_file.assert_called_with("test/path")
        j = d._json
        self.assertEqual(type(j), dict)
        self.assertEqual(j["k1"], "val1")
        self.assertEqual(j["k2"]["k3"], "val2")

    def test_endian(self):
        pass

    def test_get_types(self):
        pass

    @patch("builtins.open", new_callable=mock_open, read_data='{"k1":"val1","k2":{"k3":"val2"}}')
    def test_load_json(self, mock_file):
        j = Dwarf2JsonLoader._load_json(None, "test/path")
        # load_json attempts to open the correct file path
        mock_file.assert_called_with("test/path")
        # load_json produces the expected dict
        self.assertEqual(type(j), dict)
        self.assertEqual(j["k1"], "val1")
        self.assertEqual(j["k2"]["k3"], "val2")

    @patch("builtins.open", new_callable=mock_open, read_data="""
            {
                "base_types":{},
                "user_types":{
                    "type1":{
                        "kind":"union"
                    },
                    "type2":{
                        "kind":"struct"
                    },
                    "type3":{
                        "kind":"somekind"
                    }
                }
            }"""
            )
    def test_get_defined_struct_names(self, mock_file):
        d = Dwarf2JsonLoader("test/path")
        s = d.get_defined_struct_names()
        self.assertEqual(s, ["type1", "type2"])

    @patch("builtins.open", new_callable=mock_open, read_data="""
            {
                "base_types":{},
                "user_types":{
                    "type1":{
                        "kind":"union",
                        "fields":{
                            "f1":{
                                "offset":4
                            }
                        }
                    }
                }
            }"""
            )
    def test_get_struct_offset(self, mock_file):
        d = Dwarf2JsonLoader("test/path")
        offset = d.get_struct_offset('type1','f1')
        self.assertEqual(offset, 4)

    @patch("builtins.open", new_callable=mock_open, read_data="""
            {
                "base_types":{},
                "user_types":{
                    "type1":{
                        "kind":"union",
                        "fields":0
                        
                    },
                    "type2":{
                        "kind":"union",
                        "fields":{
                            "f1":"val1"
                        }
                    }

                }
            }"""
            )
    @patch('builtins.print')
    def test_get_struct_offset_error(self, mock_print, mock_file):
        d = Dwarf2JsonLoader("test/path")

        offset = d.get_struct_offset('type1', 'f1')
        mock_print.assert_called_with("failed to get offset for type1.f1")
        self.assertEqual(offset, None)

        offset = d.get_struct_offset('type2', 'f1')
        mock_print.assert_called_with("failed to get offset for type2.f1")
        self.assertEqual(offset, None)

        offset = d.get_struct_offset('type3', 'f1')
        mock_print.assert_called_with("failed to get offset for type3.f1")
        self.assertEqual(offset, None)

    @patch("builtins.open", new_callable=mock_open, read_data="""
            {
                "base_types":{},
                "user_types":{
                    "type1":{
                        "kind":"union",
                        "fields":0
                        
                    }
                }
            }"""
            )
    def test_get_struct_fields(self, mock_file):
        d = Dwarf2JsonLoader("test/path")
        fields = d.get_struct_fields("type1")
        self.assertEqual(fields, 0)

    @patch("builtins.open", new_callable=mock_open, read_data="""
            {
                "base_types": {
                    "_Bool": {
                      "size": 1,
                      "signed": true,
                      "kind": "bool",
                      "endian": "little"
                    },
                    "char": {
                      "size": 1,
                      "signed": false,
                      "kind": "char",
                      "endian": "little"
                    },
                    "double": {
                      "size": 8,
                      "signed": true,
                      "kind": "float",
                      "endian": "little"
                    },
                    "long int": {
                      "size": 4,
                      "signed": true,
                      "kind": "int",
                      "endian": "little"
                    }
                }
            }"""
        )
    def test_get_base_type_size(self, mock_file):
        d = Dwarf2JsonLoader("test/path")
        self.assertEqual(d.get_base_type_size('_Bool'), 1)
        self.assertEqual(d.get_base_type_size('char'), 1)
        self.assertEqual(d.get_base_type_size('double'), 8)
        self.assertEqual(d.get_base_type_size('long int'), 4)

        with self.assertRaises(Exception) as cm:
            d.get_base_type_size('bool')

        self.assertEqual(str(cm.exception), "Unable to get size for base type 'bool'")

    @patch("builtins.open", new_callable=mock_open, read_data='{"base_types":{}}')
    def test_get_field_offset(self, mock_file):
        field_attributes = {
            "offset": 0
        }
        d = Dwarf2JsonLoader("test/path")
        self.assertEqual(d.get_field_offset(field_attributes), 0)

    @patch("builtins.open", new_callable=mock_open, read_data='{"base_types":{}}')
    def test_get_field_type(self, mock_file):
        field_attributes = {
            "type": {
                "kind": "bool"
            }
        }
        d = Dwarf2JsonLoader("test/path")

        self.assertEqual(d.get_field_type(field_attributes), "bool")

    @patch("builtins.open", new_callable=mock_open, read_data='{"base_types":{}}')
    def test_get_struct_name(self, mock_file):
        field_attributes = {
            "type": {
                "name": "task_struct"
            }
        }
        d = Dwarf2JsonLoader("test/path")

        self.assertEqual(d.get_struct_name(field_attributes), "task_struct")

    @patch("builtins.open", new_callable=mock_open, read_data='{"base_types":{}}')
    def test_get_union_name(self, mock_file):
        field_attributes = {
            "type": {
                "name": "task_struct"
            }
        }
        d = Dwarf2JsonLoader("test/path")

        self.assertEqual(d.get_struct_name(field_attributes), "task_struct")

    @patch("builtins.open", new_callable=mock_open, read_data='{"base_types":{}}')
    def test_get_array_count(self, mock_file):
        field_attributes = {
            "type": {
                "count": 4,
                "subtype": {
                    "name": "unsigned int"
                }
            }
        }
        d = Dwarf2JsonLoader("test/path")

        self.assertEqual(d.get_array_count(field_attributes), 4)

    @patch("builtins.open", new_callable=mock_open, read_data='{"base_types":{}}')
    def test_get_base_type_name(self, mock_file):
        d = Dwarf2JsonLoader("test/file")
        field_attributes = {
            "type": {
                "kind": "pointer"
            }
        }
        self.assertEqual(d.get_base_type_name(field_attributes), "pointer")

        field_attributes = {
            "type": {
                "kind": "base",
                "name": "char"
            }
        }
        self.assertEqual(d.get_base_type_name( field_attributes), "char")

        field_attributes = {
            "type": {
                "kind": "struct",
                "name": "task_struct"
            }
        }
        with self.assertRaises(Exception) as cm:
            d.get_base_type_name(field_attributes)

        self.assertEqual(str(cm.exception), "Tried to get type name for kind 'struct', which is not 'pointer' or 'base'")

if __name__ == '__main__':
    unittest.main()
