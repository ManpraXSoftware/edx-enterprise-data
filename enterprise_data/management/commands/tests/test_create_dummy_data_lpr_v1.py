"""
Tests for create_dummy_data_lpr_v1 management command
"""
from unittest import TestCase, mock

from pytest import mark

from django.core.management import call_command

from enterprise_data.models import EnterpriseLearner, EnterpriseLearnerEnrollment


@mark.django_db
class TestCreateEnterpriseLearnerCommand(TestCase):
    """
    Tests to validate the behavior of `./manage.py create_dummy_data_lpr_v1` management command.
    """

    def setUp(self):
        super().setUp()
        self.uuid = 'a'*32

    def test_create_enterprise_learners_with_enrollments(self):
        """
        Management command should successfully be able to create 10 EnterpriseLearners with 5 enrollments each
        """
        assert EnterpriseLearner.objects.count() == 0
        assert EnterpriseLearnerEnrollment.objects.count() == 0

        args = [self.uuid]
        call_command('create_dummy_data_lpr_v1', *args)

        assert EnterpriseLearner.objects.count() == 10
        assert EnterpriseLearnerEnrollment.objects.count() == 50