import unittest
from unittest.mock import MagicMock, patch, call, mock_open
import sys

from monk.symbols.structs import AttributeGenerator, _name_to_camel, _gen_struct_constructor, _gen_attributes


backend_mock = MagicMock()
backend_mock.read_uint8.return_value = 8
backend_mock.read_uint16.return_value = 16
backend_mock.read_uint32.return_value = 32
backend_mock.read_uint64.return_value = 64
backend_mock.write_uint8.return_value = None
backend_mock.write_uint16.return_value = None
backend_mock.write_uint32.return_value = None
backend_mock.write_uint64.return_value = None


class TestStructs(unittest.TestCase):
    def test_get_read_fn(self):
        a = AttributeGenerator(backend_mock)
        self.assertEqual(a._get_read_fn(1), backend_mock.read_uint8)
        self.assertEqual(a._get_read_fn(2), backend_mock.read_uint16)
        self.assertEqual(a._get_read_fn(4), backend_mock.read_uint32)
        self.assertEqual(a._get_read_fn(8), backend_mock.read_uint64)
        self.assertEqual(a._get_read_fn(7), backend_mock.read_uint32)

    def test_gen_uint_prop(self):
        a = AttributeGenerator(backend_mock)
        # Test that _gen_uint_prop returns a unique function every time
        self.assertTrue(a.gen_uint_prop(0, 1) != a.gen_uint_prop(0, 1))

    def test_gen_class_prop(self):
        a = AttributeGenerator(backend_mock)
        self.assertTrue(a.gen_class_prop(0, int) != a.gen_class_prop(0, int))

    def test_gen_list_prop(self):
        a = AttributeGenerator(backend_mock)
        self.assertTrue(a.gen_list_prop(0, 1, 2) != a.gen_list_prop(0, 1, 2))

    def test_gen_null_prop(self):
        a = AttributeGenerator(backend_mock)
        self.assertTrue(a.gen_null_prop() != a.gen_null_prop())

    @patch('monk.symbols.dwarf2json_loader.Dwarf2JsonLoader')
    def test_gen_struct_constructor_ptr(self, mock_d2json):
        mock_d2json.get_struct_fields.return_value = {"f1" : {}}
        mock_d2json.get_field_type.return_value = "pointer"
        mock_d2json.get_base_type_size.return_value = 4
        mock_d2json.get_base_type_name.return_value = "int"
        mock_d2json.get_field_offset.return_value = 0

        # Create a test class using _gen_struct_constructor
        struct_name = "test_class"
        TestClass = type(struct_name, (object,), {})
        TestClass.__init__ = _gen_struct_constructor()
        TestClass.name = struct_name
        _gen_attributes(TestClass, backend_mock, mock_d2json, {struct_name: TestClass})

        # Create an instance of the class and check that the attributes read from memory
        # as expected, i.e. correct sizes, offsets, etc.
        t = TestClass(0)
        self.assertEqual(t.base, 0)
        self.assertEqual(t.name, "test_class")

        # read pointer at offset 0
        self.assertTrue(t.f1)
        backend_mock.read_uint32.assert_called_with(0)
        self.assertEqual(t.f1_offset, 0)

        # write pointer at offset 0
        t.f1 = 0x12345678
        backend_mock.write_uint32.assert_called_with(0, 0x12345678)

    @patch('monk.symbols.dwarf2json_loader.Dwarf2JsonLoader')
    def test_gen_struct_constructor_int(self, mock_d2json):
        mock_d2json.get_struct_fields.return_value = {"f2" : {}}
        mock_d2json.get_field_type.return_value = "base"
        mock_d2json.get_base_type_size.return_value = 4
        mock_d2json.get_base_type_name.return_value = "int"
        mock_d2json.get_field_offset.return_value = 1

        # Create a test class using _gen_struct_constructor
        struct_name = "test_class"
        TestClass = type(struct_name, (object,), {})
        TestClass.__init__ = _gen_struct_constructor()
        TestClass.name = struct_name
        _gen_attributes(TestClass, backend_mock, mock_d2json, {struct_name: TestClass})

        # Create an instance of the class and check that the attributes read from memory
        # as expected, i.e. correct sizes, offsets, etc.
        t = TestClass(0)
        self.assertEqual(t.base, 0)
        self.assertEqual(t.name, "test_class")

        # read uint32 at offset 1
        self.assertTrue(t.f2)
        backend_mock.read_uint32.assert_called_with(1)
        self.assertEqual(t.f2_offset, 1)

        # write uint32 at offset 1
        t.f2 = 0x12345678
        backend_mock.write_uint32.assert_called_with(1, 0x12345678)

    @patch('monk.symbols.dwarf2json_loader.Dwarf2JsonLoader')
    def test_gen_struct_constructor_long(self, mock_d2json):
        mock_d2json.get_struct_fields.return_value = {"f3" : {}}
        mock_d2json.get_field_type.return_value = "base"
        mock_d2json.get_base_type_size.return_value = 8
        mock_d2json.get_base_type_name.return_value = "long"
        mock_d2json.get_field_offset.return_value = 2

        # Create a test class using _gen_struct_constructor
        struct_name = "test_class"
        TestClass = type(struct_name, (object,), {})
        TestClass.__init__ = _gen_struct_constructor()
        TestClass.name = struct_name
        _gen_attributes(TestClass, backend_mock, mock_d2json, {struct_name: TestClass})

        # Create an instance of the class and check that the attributes read from memory
        # as expected, i.e. correct sizes, offsets, etc.
        t = TestClass(0)
        self.assertEqual(t.base, 0)
        self.assertEqual(t.name, "test_class")

        # read long at offset 2
        self.assertTrue(t.f3)
        backend_mock.read_uint64.assert_called_with(2)
        self.assertEqual(t.f3_offset, 2)

        # write long at offset 2
        t.f3 = 0x12345678
        backend_mock.write_uint64.assert_called_with(2, 0x12345678)

    @patch('monk.symbols.dwarf2json_loader.Dwarf2JsonLoader')
    def test_gen_struct_constructor_struct(self, mock_d2json):
        mock_d2json.get_struct_fields.return_value = {"f4" : {}}
        mock_d2json.get_field_type.return_value = "struct"
        mock_d2json.get_field_offset.return_value = 3
        mock_d2json.get_struct_name.return_value = "teststruct"

        # Create a mock for the test struct we specified in the config, so that 
        # struct/union attributes have a class to return
        teststruct_mock = MagicMock()
        teststruct_mock.return_value = "teststr"  # Normally would return class instance

        # Create a test class using _gen_struct_constructor
        struct_name = "test_class"
        TestClass = type(struct_name, (object,), {})
        TestClass.__init__ = _gen_struct_constructor()
        TestClass.name = struct_name
        _gen_attributes(TestClass, backend_mock, mock_d2json, {struct_name: TestClass, "teststruct": teststruct_mock})

        # Create an instance of the class and check that the attributes read from memory
        # as expected, i.e. correct sizes, offsets, etc.
        t = TestClass(0)
        self.assertEqual(t.base, 0)
        self.assertEqual(t.name, "test_class")

        # read struct at offset 3
        self.assertEqual(t.f4, "teststr")
        teststruct_mock.assert_called_with(3)
        self.assertEqual(t.f4_offset, 3)

        # write struct at offset 3
        # TODO

    @patch('monk.symbols.dwarf2json_loader.Dwarf2JsonLoader')
    def test_gen_struct_constructor_union(self, mock_d2json):
        self.skipTest("Come back to this")

        mock_d2json.get_struct_fields.return_value = {"f5" : {}}
        mock_d2json.get_field_type.return_value = "struct"
        mock_d2json.get_field_offset.return_value = 4
        mock_d2json.get_struct_name.return_value = "teststruct"

        # Create a mock for the test struct we specified in the config, so that 
        # struct/union attributes have a class to return
        teststruct_mock = MagicMock()
        teststruct_mock.return_value = "teststr"  # Normally would return class instance
        _class_type_map["teststruct"] = teststruct_mock

        # Create a test class using _gen_struct_constructor
        TestClass = type("TestClass", (object,), {})
        TestClass.__init__ = _gen_struct_constructor(TestClass, "test_class", mock_d2json)

        # Create an instance of the class and check that the attributes read from memory
        # as expected, i.e. correct sizes, offsets, etc.
        t = TestClass(0)
        self.assertEqual(t.base, 0)
        self.assertEqual(t.name, "test_class")

        # union at offset 4
        self.assertEqual(t.f5, "teststr")
        teststruct_mock.assert_called_with(4)
        self.assertEqual(t.f5_offset, 4)

        # cleanup
        _class_type_map.pop("teststruct")

    @patch('monk.symbols.dwarf2json_loader.Dwarf2JsonLoader')
    def test_gen_struct_constructor_array(self, mock_d2json):
        self.skipTest("Come back to this")

        mock_d2json.get_struct_fields.return_value = {"f6" : {}}
        mock_d2json.get_field_offset.return_value = 5
        mock_d2json.get_base_type_size.return_value = 1
        mock_d2json.get_array_count.return_value = 3
        mock_d2json.get_array_type.return_value = 'char'
        mock_d2json.get_field_type.return_value = "array"

        # Create a test class using _gen_struct_constructor
        TestClass = type("TestClass", (object,), {})
        TestClass.__init__ = _gen_struct_constructor(TestClass, "test_class", mock_d2json)

        # Create an instance of the class and check that the attributes read from memory
        # as expected, i.e. correct sizes, offsets, etc.
        t = TestClass(0)
        self.assertEqual(t.base, 0)
        self.assertEqual(t.name, "test_class")

        # array of 3 char elements at offset 5
        backend_mock.read_uint8.side_effect = [1, 2, 3]
        arr = t.f6
        self.assertEqual(arr[0], 1)
        self.assertEqual(arr[1], 2)
        self.assertEqual(arr[2], 3)
        backend_mock.read_uint8.assert_has_calls([call(5), call(6), call(7)])
        self.assertEqual(t.f6_offset, 5)

    def test_name_to_camel(self):
        self.assertEqual(_name_to_camel("test_struct"), "TestStruct")
        self.assertEqual(_name_to_camel("Test_struct"), "TestStruct")
        self.assertEqual(_name_to_camel("test_Struct"), "TestStruct")
        self.assertEqual(_name_to_camel("Test_Struct"), "TestStruct")

    @patch('builtins.open', new_callable=mock_open, read_data="""
        {
            "base_types":{
                "int":{
                    "size":4
                }
            },
            "user_types":{
                "test_struct":{
                    "kind":"struct",
                    "fields":{
                        "f1":{
                            "type":{
                                "kind":"base",
                                "name":"int"
                            },
                            "offset":0
                        }
                    }
                }
            }
        }
    """
    )
    def test_init_kernel_classes(self, mock_d2json):
        self.skipTest("Come back to this")

        init("filename")

        self.assertEqual(len(_class_type_map), 1)
        self.assertTrue('test_struct' in _class_type_map)

        from monk.symbols.structs import TestStruct
        t = TestStruct(0)
        self.assertEqual(t.f1, 32)
        backend_mock.read_uint32.assert_called_with(0)


if __name__ == '__main__':
    unittest.main()
