import importlib
import os
import unittest
from dbintegtestutils.db_handlers import get_db_handler, SUPPORTED_DBS


class DBIntegTestCase(unittest.TestCase):
    db_handler = None
    dbs_to_reset = None

    @classmethod
    def setUpClass(cls):
        """
        Initialized db integ test by:

        :return:
        """
        settings_module_path = os.environ.get('DB_TEST_SETTINGS')
        settings = importlib.import_module(settings_module_path)

        settings = cls.validate_settings(settings)

        cls.db_handler = get_db_handler(settings.DATABASE)

        for script in settings.DESTROY_DB_SCRIPTS:
            cls.db_handler.destroy_db(script)

        for script in settings.CREATE_DB_SCRIPTS:
            cls.db_handler.initialize_db(script)

        cls.dbs_to_reset = settings.RESET_DBS

        cls.settings = settings

    @classmethod
    def tearDownClass(cls):
        cls.db_handler.close()

    @classmethod
    def validate_settings(cls, settings):
        """
        :param settings:
        :return:
        """
        assert settings.DATABASE['type'] in  SUPPORTED_DBS
        return settings

    def load_fixtures(self, test_module_string):
        """
        Loads the appropriate test fixtures for the current test.
        Loading consists of opening all files with sql statements
        and executing those commands against the current db.

        Fixtures can be specified on the class level, which would
        apply against every class or per test by decorating it.

        All fixtures should specifiy filenames that will be loaded
        in reference to `fixture_dirs` in the config file.

        :param: test_module_string represents the current test as
            returned by TestCase.id() method
        :return:
        """
        # default to the class attribute
        fixture_files = getattr(self, 'FIXTURE_FILES', [])
        test_method = self._get_test_method(test_module_string)
        if hasattr(test_method, '_integ_fixture_file'):
            fixture_files.append(test_method._integ_fixture_file)

        assert fixture_files

        # make sure to load fixtures in order they were presented
        for fixture_file in fixture_files:
            fixture = os.path.join(self.settings.FIXTURES_DIR, fixture_file)
            self.db_handler.load_fixture(fixture)

    def setUp(self):
        self.db_handler.reset_dbs(self.dbs_to_reset)
        self.load_fixtures(self.id())

    def _get_test_method(self, test_module_string):
        """
        Dynamically imports test method to inspect whether it is decorated
        or not.
        """
        package_list = test_module_string.split('.')
        method_str = package_list.pop()
        klass_str = package_list.pop()
        module_str = '.'.join(package_list)
        module =  __import__(module_str, fromlist=[klass_str])
        klass = getattr(module, klass_str)
        method = getattr(klass, method_str)
        return method


class load_fixture(object):
    """
    Attaches fixture file name to wrapped function

    :param func:
    :return:
    """
    def __init__(self, fixture_name):
        self.fixture_name = fixture_name

    def __call__(self, func):
        func._integ_fixture_file = self.fixture_name
        return func
