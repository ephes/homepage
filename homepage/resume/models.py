from typing import NewType

Year = NewType("Year", int)


class SocialLink:
    def __init__(self, *, name: str, url: str, svg_icon: str):
        self.name = name
        self.url = url
        self.svg_icon = svg_icon


class Contact:
    def __init__(self, *, email: str, phone: str, social_links: list[SocialLink]):
        self.email = email
        self.phone = phone
        self.social_links = social_links


class Person:
    def __init__(
        self,
        *,
        name: str,
        initials: str,
        tagline: str,
        about: str,
        avatar_url: str,
        personal_website_url: str,
        pronouns: str,
    ):
        self.name = name
        self.initials = initials
        self.tagline = tagline
        self.about = about
        self.avatar_url = avatar_url
        self.personal_website_url = personal_website_url
        self.pronouns = pronouns


class Location:
    def __init__(self, *, name: str, url: str):
        self.name = name
        self.url = url


class Education:
    def __init__(self, *, school: str, start: Year, end: Year):
        self.school = school
        self.start = start
        self.end = end


class Company:
    def __init__(self, *, name: str, url: str):
        self.name = name
        self.url = url


class Work:
    def __init__(self, *, company: Company, title: str, start: Year, end: Year, badges: list[str], description: str):
        self.company = company
        self.title = title
        self.start = start
        self.end = end
        self.badges = badges
        self.description = description


class Timeline:
    def __init__(self, *, title: str, entries: list[Work]):
        self.title = title
        self.entries = entries


class Project:
    def __init__(self, *, title: str, url: str, description: str, badges: list[str]):
        self.title = title
        self.url = url
        self.description = description
        self.badges = badges


class Resume:
    def __init__(
        self,
        *,
        person: Person,
        location: Location,
        contact: Contact,
        education: Education,
        timelines: list[Timeline],
        skills: list[str],
        projects: list[Project],
    ):
        self.person = person
        self.location = location
        self.contact = contact
        self.education = education
        self.skills = skills
        self.timelines = timelines
        self.projects = projects


width, height = "1.25em", "1.25em"
github = SocialLink(
    name="GitHub",
    url="https://github.com/ephes/",
    svg_icon=(
        f'<svg width="{width}" height="{height}" viewBox="0 0 100 100" '
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
phone = SocialLink(
    name="Phone",
    url="tel:+4917623530319",
    svg_icon=(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide '
        'lucide-phone size-4"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 '
        "1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 "
        "1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 "
        '16.92z">'
        "</path></svg>"
    ),
)

email = SocialLink(
    name="Email",
    url="mailto:jochen-cv@wersdoerfer.de",
    svg_icon=(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide '
        'lucide-mail size-4"><rect width="20" height="16" x="2" y="4" rx="2"></rect>'
        '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path></svg>'
    ),
)
linkedin = SocialLink(
    name="LinkedIn",
    url="https://www.linkedin.com/in/jochen-wersdoerfer/",
    svg_icon=(
        f'<svg width="{width}" height="{height}" viewBox="0 0 24 24" fill="none" '
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
mastodon = SocialLink(
    name="Mastodon",
    url="https://wersdoerfer.de/@jochen",
    svg_icon=(
        f'<svg width="{width}" height="{height}" viewBox="0 0 74 79" fill="black" xmlns="http://www.w3.org/2000/svg">'
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

jochen = Person(
    name="Jochen Wersdörfer",
    initials="JW",
    tagline=(
        "Freelance Software developer doing mostly data science " "/ machine learning and web development using Django"
    ),
    about=(
        "As a long term Python developer I've seen a lot of different projects over the "
        "years. And I always had a lot of fun building stuff, never thinking of my work "
        "just as a job. Nowadays I mostly work with Python, but don't mind using other "
        "languages and tools to build complete products."
    ),
    avatar_url=("https://d2b7dn9rofvhjd.cloudfront.net/images" "/Jochen_Profil_Dunkel_Quadratisch.original.jpg"),
    personal_website_url="https://wersdoerfer.de",
    pronouns="he/him",
)
duesseldorf = Location(
    name="Düsseldorf, Germany, CET",
    url="https://www.google.com/maps/place/D%C3%BCsseldorf/",
)
contact = Contact(
    email="jochen-cv@wersdoerfer.de",
    phone="+4917623530319",
    social_links=[
        email,
        phone,
        github,
        linkedin,
        mastodon,
    ],
)
freelance = Timeline(
    title="Freelance Work Experience",
    entries=[
        Work(
            company=Company(name="Pixolus", url="https://pixolus.de/en/"),
            title="Senior Software Developer",
            start=Year(2024),
            end=Year(2024),
            description=(
                "Single Sign On Integration using "
                '<a href="https://github.com/grafana/django-saml2-auth">django-saml2-auth</a> '
                'and <a href="https://github.com/IdentityPython/pysaml2">PySAML2</a>.'
            ),
            badges=["Remote"],
        ),
        Work(
            company=Company(name="Systemiq", url="https://www.systemiq.earth/"),
            title="Senior Software Architect",
            start=Year(2022),
            end=Year(2024),
            description="Software architecture for advanced economic models.",
            badges=["Remote"],
        ),
        Work(
            company=Company(name="Exkulpa", url="https://exkulpa.de/"),
            title="Senior Software Developer",
            start=Year(2023),
            end=Year(2023),
            description="Building a web based system to collect information about hazards in the workplace.",
            badges=["Remote"],
        ),
        Work(
            company=Company(name="Heinrich Heine Universität Düsseldorf", url="https://www.hhu.de/"),
            title="Trainer",
            start=Year(2022),
            end=Year(2022),
            description="Workshop on how to use PyTest.",
            badges=["In Person"],
        ),
        Work(
            company=Company(name="Linuxhotel", url="https://www.linuxhotel.de/"),
            title="Trainer",
            start=Year(2021),
            end=Year(2022),
            description=("Introduction to the Python Programming Language."),
            badges=["In Person"],
        ),
        Work(
            company=Company(name="Covid IT Solutions GmbH", url="https://cov-it.de/"),
            title="Senior Software Developer",
            start=Year(2022),
            end=Year(2022),
            description=(
                "Working on a new system to improve contact tracing for "
                "public health offices using Django and HTMX to be able to "
                "handle complex forms."
            ),
            badges=["Remote"],
        ),
        Work(
            company=Company(name="RTL", url="https://www.rtl.de/"),
            title="Senior Software Developer",
            start=Year(2020),
            end=Year(2021),
            description=("Building a system for context aware advertisement."),
            badges=["In Person", "Remote"],
        ),
        Work(
            company=Company(name="Dirk Brennemann", url=None),
            title="Senior Software Developer",
            start=Year(2018),
            end=Year(2019),
            description=("Automatic receipt handling."),
            badges=["Remote"],
        ),
        Work(
            company=Company(name="Trivago", url="https://www.trivago.com/"),
            title="Senior Data Scientist / Product Owner",
            start=Year(2016),
            end=Year(2017),
            description=(
                "Machine learning models for automatic bidding for clicks on hotel rooms."
                "A system for setting hotel room prices automatically based on forecasting."
            ),
            badges=["In Person"],
        ),
        Work(
            company=Company(name="Shop.co", url=None),
            title="Senior Data Scientist",
            start=Year(2015),
            end=Year(2016),
            description=("Machine learning models for extracting structured data from product detail pages."),
            badges=["In Person"],
        ),
        Work(
            company=Company(name="Otto Group", url="https://www.ottogroup.com/"),
            title="Senior Data Scientist",
            start=Year(2015),
            end=Year(2015),
            description=("Machine learning models for prediction of user attributes."),
            badges=["In Person"],
        ),
        Work(
            company=Company(name="Pixolus", url="https://pixolus.de/"),
            title="Senior Software Developer",
            start=Year(2014),
            end=Year(2015),
            description=("Django restframework based API for mobile clients."),
            badges=["In Person"],
        ),
        Work(
            company=Company(
                name="Institut für Nachrichtentechnik RWTH Aachen", url="https://www.ient.rwth-aachen.de/"
            ),
            title="Senior Software Developer",
            start=Year(2014),
            end=Year(2014),
            description=("Django restframework based API for mobile clients."),
            badges=["In Person"],
        ),
        Work(
            company=Company(name="prinz.de", url="https://prinz.de/"),
            title="Senior Software Developer",
            start=Year(2013),
            end=Year(2013),
            description=("Django backend for events website."),
            badges=["Remote"],
        ),
    ],
)
employed = Timeline(
    title="Employed Work Experience",
    entries=[
        Work(
            company=Company(name="billiger.de", url="https://billiger.de"),
            title="Senior Software Developer",
            start=Year(2005),
            end=Year(2011),
            description="Backend development and machine learning.",
            badges=[],
        ),
        Work(
            company=Company(name="web.de", url="https://web.de"),
            title="System Administrator / Systems Programmer",
            start=Year(2001),
            end=Year(2004),
            description="Lifecycle management, monitoring and deployment.",
            badges=[],
        ),
    ],
)

projects = [
    Project(
        title="Python Podcast",
        url="https://python-podcast.de/show",
        description="A popular german speaking podcast about Python",
        badges=[
            "Side Project",
            "Python",
        ],
    ),
    Project(
        title="django-cast",
        url="https://github.com/ephes/django-cast",
        description="A podcast hosting platform built with Django and Wagtail",
        badges=[
            "Side Project",
            "Python",
            "Django",
            "Wagtail",
        ],
    ),
    Project(
        title="PlastInvest",
        url="https://plastinvest.global/",
        description=(
            "PlastInvest is a tool for governments, providing quantitative and qualitative insights into "
            "the investments needed to deliver national action plans for reducing plastic waste and "
            "pollution."
        ),
        badges=[
            "Systemiq",
            "Python",
            "Django",
            "htmx",
        ],
    ),
    Project(
        title="Data Science Tutorial",
        url="",
        description=(
            "This tutorial covers topics that are relevant or interesting for me for '"
            "some kind of reason 😄. Have fun!"
        ),
        badges=[
            "Side Project",
            "Python",
            "Jupyter",
            "nbdev",
            "Pandas",
            "NumPy",
            "scikit-learn",
            "keras",
        ],
    ),
    Project(
        title="kptncook",
        url="https://github.com/ephes/kptncook",
        description=("A small command line client for downloading KptnCook recipes."),
        badges=[
            "Side Project",
            "Python",
            "Pydantic",
        ],
    ),
    Project(
        title="PlasticIQ",
        url="https://plasticiq.global/",
        description="Plastic IQ is a data-driven digital platform to help companies end plastic waste.",
        badges=[
            "Systemiq",
            "Python",
            "Django",
            "htmx",
        ],
    ),
    Project(
        title="fastdeploy",
        url="https://github.com/ephes/fastdeploy",
        description="A web backend for deploying projects automatically and showing realtime progress to the user.",
        badges=[
            "Side Project",
            "Python",
            "fastapi",
            "sqlalchemy",
            "Vue.js",
        ],
    ),
    Project(
        title="cast-vue",
        url="https://github.com/ephes/cast-vue",
        description="A Vue.js frontend for django-cast",
        badges=[
            "Side Project",
            "Vue.js",
            "TypeScript",
        ],
    ),
    Project(
        title="Konektom",
        url="https://konektom.org/",
        description="Konektom.org is a collaborative bookmarking service.",
        badges=[
            "Side Project",
            "Python",
            "Django",
        ],
    ),
]
resume = Resume(
    person=jochen,
    location=duesseldorf,
    contact=contact,
    education=Education(school="Universität Karlsruhe (TH)", start=Year(1997), end=Year(2001)),
    timelines=[freelance, employed],
    skills=["Python", "Django", "scikit-learn", "Pandas", "NumPy", "keras", "PyTorch", "Vue.js", "SQL"],
    projects=projects,
)


def get_resume():
    return resume
