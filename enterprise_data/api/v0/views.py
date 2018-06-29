# -*- coding: utf-8 -*-
"""
Views for enterprise api version 0 endpoint.
"""
from __future__ import absolute_import, unicode_literals

from datetime import date, timedelta
from logging import getLogger

from edx_rest_framework_extensions.authentication import JwtAuthentication
from edx_rest_framework_extensions.paginators import DefaultPagination
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from enterprise_data.api.v0 import serializers
from enterprise_data.filters import ConsentGrantedFilterBackend
from enterprise_data.models import EnterpriseEnrollment
from enterprise_data.permissions import IsStaffOrEnterpriseUser

LOGGER = getLogger(__name__)


class EnterpriseViewSet(viewsets.ViewSet):
    """
    Base class for all Enterprise view sets.
    """
    authentication_classes = (JwtAuthentication,)
    filter_backends = (ConsentGrantedFilterBackend,)
    pagination_class = DefaultPagination
    permission_classes = (IsStaffOrEnterpriseUser,)
    CONSENT_GRANTED_FILTER = 'consent_granted'

    def filter_queryset(self, queryset):
        """
        Filters queryset to only return consenting learners.
        """
        return ConsentGrantedFilterBackend().filter_queryset(self.request, queryset, view=self)

    def ensure_data_exists(self, request, data, error_message=None):
        """
        Ensure that the API response brings us valid data. If not, raise an error and log it.
        """
        if not data:
            error_message = (
                error_message or "Unable to fetch API response from endpoint '{}'.".format(request.get_full_path())
            )
            LOGGER.error(error_message)
            raise NotFound(error_message)


class EnterpriseEnrollmentsViewSet(EnterpriseViewSet, viewsets.ModelViewSet):
    """
    Viewset for routes related to Enterprise course enrollments.
    """
    serializer_class = serializers.EnterpriseEnrollmentSerializer

    def get_queryset(self):
        """
        Returns all learner enrollment records for a given enterprise.
        """
        enterprise_id = self.kwargs['enterprise_id']
        enrollments = EnterpriseEnrollment.objects.filter(enterprise_id=enterprise_id)
        enrollments = self.filter_queryset(enrollments)
        self.ensure_data_exists(
            self.request,
            enrollments,
            error_message=(
                "No course enrollments are associated with Enterprise {enterprise_id} from endpoint '{path}'."
                .format(
                    enterprise_id=enterprise_id,
                    path=self.request.get_full_path()
                )
            )
        )
        return enrollments

    def filter_distinct_learners(self, queryset):
        """
        Filters queryset to include enrollments with a distinct `enterprise_user_id`.
        """
        return queryset.values_list('enterprise_user_id', flat=True).distinct()

    def filter_active_learners(self, queryset, last_activity_date):
        """
        Filters queryset to include enrollments more recent than the specified `last_activity_date`.
        """
        return self.filter_distinct_learners(
            queryset.filter(last_activity_date__gte=last_activity_date)
        )

    def filter_course_completions(self, queryset):
        """
        Filters queryset to include only enrollments that are passing (i.e., completion).
        """
        return queryset.filter(has_passed=1)

    def subtract_one_month(self, original_date):
        """
        Returns a date exactly one month prior to the passed in date.
        """
        one_day = timedelta(days=1)
        one_month_earlier = original_date - one_day
        while one_month_earlier.month == original_date.month or one_month_earlier.day > original_date.day:
            one_month_earlier -= one_day
        return one_month_earlier

    @list_route()
    def overview(self, request, **kwargs):  # pylint: disable=unused-argument
        """
        Returns the following data:
            - # of enrolled learners;
            - # of active learners in the past week/month;
            - # of course completions.
        """
        enrollments = self.get_queryset()
        course_completions = self.filter_course_completions(enrollments)
        distinct_learners = self.filter_distinct_learners(enrollments)
        past_week_date = date.today() - timedelta(weeks=1)
        past_month_date = self.subtract_one_month(date.today())
        active_learners_week = self.filter_active_learners(enrollments, past_week_date)
        active_learners_month = self.filter_active_learners(enrollments, past_month_date)

        content = {
            'enrolled_learners': distinct_learners.count(),
            'active_learners': {
                'past_week': active_learners_week.count(),
                'past_month': active_learners_month.count(),
            },
            'course_completions': course_completions.count(),
        }
        return Response(content)