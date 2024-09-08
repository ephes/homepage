import random
import string
from functools import partial

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SocialLink:
    def __init__(self, *, name: str, url: str, svg_icon: str, width: str = "1.25em", height: str = "1.25em"):
        self.name = name
        self.url = url
        self.svg_icon = svg_icon.format(width=width, height=height)
        self.width = width
        self.height = height


EmailLink = partial(
    SocialLink,
    name="Email",
    svg_icon=(
        '<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide '
        'lucide-mail size-4"><rect width="20" height="16" x="2" y="4" rx="2"></rect>'
        '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path></svg>'
    ),
)


PhoneLink = partial(
    SocialLink,
    name="Phone",
    svg_icon=(
        '<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide '
        'lucide-phone size-4"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 '
        "1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 "
        "1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 "
        '16.92z">'
        "</path></svg>"
    ),
)

GithubLink = partial(
    SocialLink,
    name="GitHub",
    svg_icon=(
        '<svg width="{width}" height="{height}" viewBox="0 0 100 100" '
        'xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" '
        'd="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 '
        "3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-"
        "5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.5"
        "23 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 "
        "3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-."
        "485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 "
        "12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2."
        "67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 "
        "23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 "
        "0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75."
        '788 0 48.854 0z" fill="#24292f"/></svg>'
    ),
)

LinkedInLink = partial(
    SocialLink,
    name="LinkedIn",
    svg_icon=(
        '<svg width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg"><path d="M18.72 3.99997H5.37C5.19793 '
        "3.99191 5.02595 4.01786 4.86392 4.07635C4.70189 4.13484 4.55299 4.22471 "
        "4.42573 4.34081C4.29848 4.45692 4.19537 4.59699 4.12232 4.75299C4.04927 "
        "4.909 4.0077 5.07788 4 5.24997V18.63C4.01008 18.9901 4.15766 19.3328 "
        "4.41243 19.5875C4.6672 19.8423 5.00984 19.9899 5.37 20H18.72C19.0701 "
        "19.9844 19.4002 19.8322 19.6395 19.5761C19.8788 19.32 20.0082 18.9804 "
        "20 18.63V5.24997C20.0029 5.08247 19.9715 4.91616 19.9078 4.76122C19.8441 "
        "4.60629 19.7494 4.466 19.6295 4.34895C19.5097 4.23191 19.3672 4.14059 "
        "19.2108 4.08058C19.0544 4.02057 18.8874 3.99314 18.72 3.99997ZM9 "
        "17.34H6.67V10.21H9V17.34ZM7.89 9.12997C7.72741 9.13564 7.5654 9.10762 "
        "7.41416 9.04768C7.26291 8.98774 7.12569 8.89717 7.01113 8.78166C6.89656 "
        "8.66615 6.80711 8.5282 6.74841 8.37647C6.6897 8.22474 6.66301 8.06251 "
        "6.67 7.89997C6.66281 7.73567 6.69004 7.57169 6.74995 7.41854C6.80986 "
        "7.26538 6.90112 7.12644 7.01787 7.01063C7.13463 6.89481 7.2743 6.80468 "
        "7.42793 6.74602C7.58157 6.68735 7.74577 6.66145 7.91 6.66997C8.07259 "
        "6.66431 8.2346 6.69232 8.38584 6.75226C8.53709 6.8122 8.67431 6.90277 "
        "8.78887 7.01828C8.90344 7.13379 8.99289 7.27174 9.05159 7.42347C9.1103 "
        "7.5752 9.13699 7.73743 9.13 7.89997C9.13719 8.06427 9.10996 8.22825 "
        "9.05005 8.3814C8.99014 8.53456 8.89888 8.6735 8.78213 8.78931C8.66537 "
        "8.90513 8.5257 8.99526 8.37207 9.05392C8.21843 9.11259 8.05423 9.13849 "
        "7.89 9.12997ZM17.34 17.34H15V13.44C15 12.51 14.67 11.87 13.84 11.87C13.5822 "
        "11.8722 13.3313 11.9541 13.1219 12.1045C12.9124 12.2549 12.7546 12.4664 "
        "12.67 12.71C12.605 12.8926 12.5778 13.0865 12.59 13.28V17.34H10.29V10.21H12."
        "59V11.21C12.7945 10.8343 13.0988 10.5225 13.4694 10.3089C13.84 10.0954 "
        '14.2624 9.98848 14.69 9.99997C16.2 9.99997 17.34 11 17.34 13.13V17.34Z" '
        'fill="#000000"/></svg>'
    ),
)

MastodonLink = partial(
    SocialLink,
    name="Mastodon",
    svg_icon=(
        '<svg width="{width}" height="{height}" viewBox="0 0 74 79" fill="black" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M73.7014 17.4323C72.5616 9.05152 65.1774 2.4469 56.424 1.1671C54.9472 0.950843 49.3518 0.163818 '
        "36.3901 0.163818H36.2933C23.3281 0.163818 20.5465 0.950843 19.0697 1.1671C10.56 2.41145 2.78877 8.34604 "
        "0.903306 16.826C-0.00357854 21.0022 -0.100361 25.6322 0.068112 29.8793C0.308275 35.9699 0.354874 42.0498 "
        "0.91406 48.1156C1.30064 52.1448 1.97502 56.1419 2.93215 60.0769C4.72441 67.3445 11.9795 73.3925 19.0876 "
        "75.86C26.6979 78.4332 34.8821 78.8603 42.724 77.0937C43.5866 76.8952 44.4398 76.6647 45.2833 76.4024C47.1867 "
        "75.8033 49.4199 75.1332 51.0616 73.9562C51.0841 73.9397 51.1026 73.9184 51.1156 73.8938C51.1286 73.8693 "
        "51.1359 73.8421 51.1368 73.8144V67.9366C51.1364 67.9107 51.1302 67.8852 51.1186 67.862C51.1069 67.8388 "
        "51.0902 67.8184 51.0695 67.8025C51.0489 67.7865 51.0249 67.7753 50.9994 67.7696C50.9738 67.764 50.9473 "
        "67.7641 50.9218 67.7699C45.8976 68.9569 40.7491 69.5519 35.5836 69.5425C26.694 69.5425 24.3031 65.3699 "
        "23.6184 63.6327C23.0681 62.1314 22.7186 60.5654 22.5789 58.9744C22.5775 58.9477 22.5825 58.921 22.5934 "
        "58.8965C22.6043 58.8721 22.621 58.8505 22.6419 58.8336C22.6629 58.8167 22.6876 58.8049 22.714 58.7992C "
        "22.7404 "
        "58.7934 22.7678 58.794 22.794 58.8007C27.7345 59.9796 32.799 60.5746 37.8813 60.5733C39.1036 60.5733 "
        "40.3223 60.5733 41.5447 60.5414C46.6562 60.3996 52.0437 60.1408 57.0728 59.1694C57.1983 59.1446 57.3237 "
        "59.1233 57.4313 59.0914C65.3638 57.5847 72.9128 52.8555 73.6799 40.8799C73.7086 40.4084 73.7803 35.9415 "
        "73.7803 35.4523C73.7839 33.7896 74.3216 23.6576 73.7014 17.4323ZM61.4925 47.3144H53.1514V27.107C53.1514 "
        "22.8528 51.3591 20.6832 47.7136 20.6832C43.7061 20.6832 41.6988 23.2499 41.6988 28.3194V39.3803H33.4078V28"
        ".3194C33.4078 23.2499 31.3969 20.6832 27.3894 20.6832C23.7654 20.6832 21.9552 22.8528 21.9516 27.107V47."
        "3144H13.6176V26.4937C13.6176 22.2395 14.7157 18.8598 16.9118 16.3545C19.1772 13.8552 22.1488 12.5719 "
        "25.8373 12.5719C30.1064 12.5719 33.3325 14.1955 35.4832 17.4394L37.5587 20.8853L39.6377 17.4394C41.7884 "
        "14.1955 45.0145 12.5719 49.2765 12.5719C52.9614 12.5719 55.9329 13.8552 58.2055 16.3545C60.4017 18.8574 "
        '61.4997 22.2371 61.4997 26.4937L61.4925 47.3144Z" fill="inherit"/>'
        "</svg>"
    ),
)


class Person(models.Model):
    """
    Model to store the personal information of the person.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    pronouns = models.CharField(max_length=20)
    tagline = models.CharField(max_length=512)
    about = models.TextField()
    avatar_url = models.URLField()
    avatar_alt = models.CharField(max_length=255)
    location_name = models.CharField(max_length=255)
    location_url = models.URLField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField()
    github = models.URLField()
    linkedin = models.URLField()
    mastodon = models.URLField()
    skills = models.CharField(max_length=512, default="")
    education_school_name = models.CharField(max_length=255, default="")
    education_school_url = models.URLField(null=True, blank=True)
    education_start = models.PositiveIntegerField(
        validators=[MinValueValidator(1997), MaxValueValidator(2030)],
        default=2016,
    )
    education_end = models.PositiveIntegerField(
        validators=[MinValueValidator(2001), MaxValueValidator(2030)],
        default=2020,
    )

    def __repr__(self):
        return f"<{self.name}>"

    def __str__(self):
        return self.name

    @property
    def skills_list(self):
        return self.skills.split(",") if self.skills else []

    @property
    def social_links(self):
        links = [
            EmailLink(url=f"mailto:{self.email}"),
            PhoneLink(url=f"tel:{self.phone}"),
            GithubLink(url=self.github),
            LinkedInLink(url=self.linkedin),
            MastodonLink(url=self.mastodon),
        ]
        return links


def generate_random_string(length=20):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class CVToken(models.Model):
    """
    Model to store tokens for accessing the CV. The token is just a random string.
    If you want to give someone access to the CV, you can generate a token and send it to them.
    Please note the receiver in the model so you know who you gave access to.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="cv_tokens")
    token = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    receiver = models.CharField(max_length=255)

    def __str__(self):
        return self.token

    def save(self, *args, **kwargs):
        self.token = generate_random_string()
        super().save(*args, **kwargs)


class Timeline(models.Model):
    """
    Model to store the timeline of the person.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="timelines")
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField(
        default=0, unique=True, help_text="Position of the timeline in the list of timelines."
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["person", "position"], name="unique_timeline_position")]

    def __repr__(self):
        return f"{self.person.name} - {self.title}"

    def __str__(self):
        return self.title

    @property
    def ordered_entries(self):
        return self.entries.order_by("position")


class TimelineEntry(models.Model):
    """
    Model to store the timeline entries.
    """

    timeline = models.ForeignKey(Timeline, on_delete=models.CASCADE, related_name="entries")
    company_name = models.CharField(max_length=255)
    company_url = models.URLField(null=True, blank=True)
    role = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0, help_text="Position of the entry in the timeline.")
    start = models.PositiveIntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2030)])
    end = models.PositiveIntegerField(validators=[MinValueValidator(2001), MaxValueValidator(2030)])
    description = models.TextField()
    badges = models.CharField(max_length=255, default="", blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["timeline", "position"], name="unique_timeline_entry_position")]

    def __repr__(self):
        return f"{self.company_name} - {self.role}"

    def __str__(self):
        return repr(self)

    @property
    def badges_list(self):
        return self.badges.split(",") if self.badges else []


class Project(models.Model):
    """
    Model to store the projects of the person.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=255)
    url = models.URLField()
    description = models.TextField()
    position = models.PositiveIntegerField(default=0, help_text="Position of the project in the list of projects.")
    badges = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["person", "position"], name="unique_project_position")]

    def __repr__(self):
        return self.title

    def __str__(self):
        return repr(self)

    @property
    def badges_list(self):
        return self.badges.split(",") if self.badges else []
