import ddt
import mock
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from course_discovery.apps.core.tests.factories import UserFactory
from course_discovery.apps.course_metadata.tests import toggle_switch
from course_discovery.apps.publisher.choices import PublisherUserRole
from course_discovery.apps.publisher.models import CourseUserRole
from course_discovery.apps.publisher.tests import factories
from course_discovery.apps.publisher.tests.factories import UserAttributeFactory
from course_discovery.apps.publisher_comments.tests.factories import CommentFactory


@ddt.ddt
class CommentsEmailTests(TestCase):
    """ Tests for the e-mail functionality for course, course-run and seats. """

    def setUp(self):
        super(CommentsEmailTests, self).setUp()

        self.user = UserFactory()
        self.user_2 = UserFactory()
        self.user_3 = UserFactory()

        self.site = Site.objects.get(pk=settings.SITE_ID)

        self.organization_extension = factories.OrganizationExtensionFactory()

        self.seat = factories.SeatFactory()
        self.course_run = self.seat.course_run
        self.course = self.course_run.course

        # assign the role against a course
        factories.CourseUserRoleFactory(
            course=self.course, role=PublisherUserRole.MarketingReviewer, user=self.user
        )
        factories.CourseUserRoleFactory(
            course=self.course, role=PublisherUserRole.PartnerCoordinator, user=self.user_2
        )

        factories.CourseUserRoleFactory(
            course=self.course, role=PublisherUserRole.Publisher, user=self.user_3
        )

        self.course.organizations.add(self.organization_extension.organization)

        # NOTE: We intentionally do NOT create an attribute for user_2.
        # By default this user WILL receive email notifications.

        UserAttributeFactory(user=self.user, enable_email_notification=True)
        UserAttributeFactory(user=self.user_3, enable_email_notification=False)
        toggle_switch('enable_publisher_email_notifications', True)

    def test_course_comment_email(self):
        """ Verify that after adding a comment against a course emails send
        to multiple users depending upon the course related group.
        """
        comment = self.create_comment(content_object=self.course)
        subject = 'New comment added in Course: {title}'.format(title=self.course.title)
        self.assert_comment_email_sent(
            self.course, comment, reverse('publisher:publisher_courses_edit', args=[self.course.id]),
            subject
        )

    def test_course_run_comment_email(self):
        """ Verify that after adding a comment against a course-run emails send to multiple users
        depending upon the parent course related group.
        """
        comment = self.create_comment(content_object=self.course_run)
        subject = 'New comment added in course run: {title}-{pacing_type}-{start}'.format(
            title=self.course_run.course.title,
            pacing_type=self.course_run.get_pacing_type_display(),
            start=self.course_run.start.strftime('%B %d, %Y')
        )
        self.assert_comment_email_sent(
            self.course_run, comment,
            reverse('publisher:publisher_course_run_detail', args=[self.course_run.id]),
            subject
        )

    @mock.patch('course_discovery.apps.publisher_comments.models.send_email_for_comment')
    def test_email_with_enable_waffle_switch(self, send_email_for_comment):
        """ Verify that send_email_for_comment called with enable waffle switch.. """
        comment = self.create_comment(content_object=self.course)
        send_email_for_comment.assert_called_once_with(comment, True)

    @mock.patch('course_discovery.apps.publisher_comments.models.send_email_for_comment')
    def test_email_with_disable_waffle_switch(self, send_email_for_comment):
        """ Verify that send_email_for_comment not called with disable waffle switch.. """
        toggle_switch('enable_publisher_email_notifications', False)
        self.create_comment(content_object=self.course)
        send_email_for_comment.assert_not_called()

    def test_email_without_any_role(self):
        """ Verify the emails behaviour if course role has no users. """
        CourseUserRole.objects.all().delete()

        self.create_comment(content_object=self.course)
        self.assertEqual(len(mail.outbox), 0)

    def test_course_run_without_start_date(self):
        """ Verify that emails works properly even if course-run does not have a start date."""
        self.course_run.start = None
        self.course_run.save()
        comment = self.create_comment(content_object=self.course_run)
        subject = 'New comment added in course run: {title}-{pacing_type}-{start}'.format(
            title=self.course_run.course.title,
            pacing_type=self.course_run.get_pacing_type_display(),
            start=''
        )
        self.assert_comment_email_sent(
            self.course_run, comment,
            reverse('publisher:publisher_course_run_detail', args=[self.course_run.id]),
            subject
        )

    def assert_comment_email_sent(self, content_object, comment, object_path, subject):
        """ DRY method to assert send email data"""
        object_type = content_object.__class__.__name__
        self.assertEqual([self.user.email, self.user_2.email], mail.outbox[0].to)
        self.assertEqual(str(mail.outbox[0].subject), subject)
        body = mail.outbox[0].body.strip()
        heading = '{first_name} commented on a {object_type} belonging to the course {title} ({number})'
        self.assertIn(
            heading.format(
                first_name=comment.user.first_name, object_type=object_type.lower(),
                title=self.course.title, number=self.course.number
            ),
            body
        )
        page_url = 'https://{host}{path}'.format(host=comment.site.domain.strip('/'), path=object_path)
        self.assertIn(comment.comment, body)
        self.assertIn(page_url, body)
        self.assertIn('The edX team', body)

    def test_email_with_roles(self):
        """ Verify that emails send to the users against course-user-roles also."""
        user_4 = UserFactory()
        user_5 = UserFactory()

        # assign the role against a course
        factories.CourseUserRoleFactory(
            course=self.course, role=PublisherUserRole.MarketingReviewer, user=user_4
        )
        factories.CourseUserRoleFactory(
            course=self.course, role=PublisherUserRole.PartnerCoordinator, user=user_5
        )
        self.create_comment(content_object=self.course_run)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual([self.user.email, self.user_2.email, user_4.email, user_5.email], mail.outbox[0].to)

    def test_email_for_roles_only(self):
        """ Verify the emails send to the course roles users even if groups has no users. """
        user_4 = UserFactory()
        # assign the role against a course
        factories.CourseUserRoleFactory(
            course=self.course, role=PublisherUserRole.MarketingReviewer, user=user_4
        )

        self.create_comment(content_object=self.course)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_with_course_comment_editing(self):
        """ Verify that after editing a comment against a course emails send
        to multiple users.
        """
        comment = self.create_comment(content_object=self.course)
        subject = 'New comment added in Course: {title}'.format(title=self.course.title)
        self.assertEqual(str(mail.outbox[0].subject), subject)
        self.assertIn(comment.comment, str(mail.outbox[0].body.strip()))

        comment.comment = 'update the comment'
        comment.save()  # pylint: disable=no-member
        subject = 'Comment updated in Course: {title}'.format(title=self.course.title)
        self.assertEqual(str(mail.outbox[1].subject), subject)
        self.assertIn(comment.comment, str(mail.outbox[1].body.strip()), 'update the comment')

    def test_email_with_course_run_comment_editing(self):
        """ Verify that after editing a comment against a course emails send
        to multiple users.
        """
        comment = self.create_comment(content_object=self.course_run)
        comment.comment = 'Update the comment'
        comment.save()  # pylint: disable=no-member

        subject = 'Comment updated in course run: {title}-{pacing_type}-{start}'.format(
            title=self.course_run.course.title,
            pacing_type=self.course_run.get_pacing_type_display(),
            start=self.course_run.start.strftime('%B %d, %Y')
        )
        self.assertEqual(str(mail.outbox[1].subject), subject)
        self.assertIn(comment.comment, str(mail.outbox[1].body.strip()), 'Update the comment')

    def create_comment(self, content_object):
        """ DRY method to create the comment for a given content type."""
        return CommentFactory(
            content_object=content_object, user=self.user, site=self.site
        )