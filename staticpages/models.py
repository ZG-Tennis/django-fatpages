from django.db import models
# from django.contrib.sites.models import Site
import os
import re
from django.utils.translation import ugettext_lazy as _
from ckeditor.fields import RichTextField

from django.conf import settings
from generics.s3utils import Go_S3
from generics.analyze_html import Analyze_HTML


go_s3=Go_S3()

# LOGGING
from settings_logging import the_logging
logger = the_logging.getLogger(__name__)


class FatPage(models.Model):
    url = models.CharField(_('URL'), max_length=100, db_index=True)
    title = models.CharField(_('title'), max_length=200)
    content = RichTextField(null=True, blank=True)
    excerpt = RichTextField("mobile content", null=True, blank=True, help_text="Used for mobile site")
    enable_comments = models.BooleanField(_('enable comments'))
    template_name = models.CharField(_('template name'), max_length=70, blank=True,
                                     help_text=_("Example: 'staticpages/contact_page.html'. If this isn't provided, the system will use 'the default."))

    registration_required = models.BooleanField(_('registration required'), help_text=_("If this is checked, only logged-in users will be able to view the page."))

    class Meta:
        db_table = 'django_flatpage'
        verbose_name = _('static page')
        verbose_name_plural = _('static pages')
        ordering = ('url',)

    def __unicode__(self):
        return u"%s -- %s" % (self.url, self.title)

    def get_absolute_url(self):
        return self.url


    match_urls = re.compile(r'(^%s)' % settings.MEDIA_URL)

    analyze_html = Analyze_HTML()

    def save(self, *args, **kwargs):
        # replacing any instance of https://ace with cdn for the management server
        logger.info("Starting to save static page: %s" % self.title)
        logger.info("ENABLE_S3: %s" % settings.ENABLE_S3)

        if settings.ENABLE_S3:

            #connecting to s3
            go_s3.connect_to_s3()
            logger.info("Logged to S3")

            # DEALING WITH CKEDITOR
            #Finding all image URLs inside the dom that are uploaded to local or management server at this point
            self.analyze_html.set_html(self.content)
            all_local_imgs = self.analyze_html.find_tag_with_attr_that_matches(tag='img', attr='src', the_match=self.match_urls)

            
            for img in all_local_imgs:
                i = img['src'].replace(settings.MEDIA_URL, "")   #getting the path of the file.

                logger.info("file in CKEDITOR to be uploaded: %s" % i)
                #uploading the file
                try:
                    go_s3.upload_file(os.path.join(settings.MEDIA_ROOT, i),
                        os.path.join(settings.MEDIA_ROOT_BASE, i),
                        del_after_upload=True,
                        )
                    #Updating img URL to point to CDN
                    img['src'] = settings.CDN_URL_UPLOADS + i
                except:
                    logger.error("Unexpected error dealing with s3 upload: ", exc_info=True)
                    pass

            #Updating Image URLS inside the article to point to the cloud
            #self.content = self.content.replace(settings.MEDIA_URL,settings.CDN_URL_UPLOADS)
            self.content = self.analyze_html.get_html()




            self.analyze_html.set_html(self.excerpt)
            all_local_imgs = self.analyze_html.find_tag_with_attr_that_matches(tag='img', attr='src', the_match=self.match_urls)

            
            for img in all_local_imgs:
                i = img['src'].replace(settings.MEDIA_URL, "")   #getting the path of the file.

                logger.info("file in CKEDITOR to be uploaded: %s" % i)
                #uploading the file
                try:
                    go_s3.upload_file(os.path.join(settings.MEDIA_ROOT, i),
                        os.path.join(settings.MEDIA_ROOT_BASE, i),
                        del_after_upload=True,
                        )
                    #Updating img URL to point to CDN
                    img['src'] = settings.CDN_URL_UPLOADS + i
                except:
                    logger.error("Unexpected error dealing with s3 upload: ", exc_info=True)
                    pass

            #Updating Image URLS inside the article to point to the cloud
            self.excerpt = self.analyze_html.get_html()




            go_s3.close_connection()


        super(FatPage, self).save(self, *args, **kwargs)
