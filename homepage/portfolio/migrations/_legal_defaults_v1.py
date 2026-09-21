"""Frozen legal-page defaults for the pre-structural-contact migration state.

Migration 0022 replaces the embedded e-mail links below with a structural contact
block.  Earlier migration states do not know that block type, so their defaults
must remain independent from the live model helpers.
"""


PLACEHOLDER_EMAIL = "portfolio-contact@example.invalid"
PLACEHOLDER_LABEL = "[globale Kontaktadresse]"


def _mail_link(prefix="E-Mail:", suffix=""):
    return (
        f'{prefix} <a href="mailto:{PLACEHOLDER_EMAIL}">'
        f"{PLACEHOLDER_LABEL}</a>{suffix}"
    )


def default_imprint_sections():
    """Return the immutable v1 Impressum default."""

    return [
        (
            "section",
            {
                "heading": "Anbieterin",
                "copy": [
                    (
                        "paragraph",
                        "<p>Angaben gemäß § 5 Digitale-Dienste-Gesetz (DDG)</p>",
                    ),
                    (
                        "address",
                        "<p>Katharina Wersdörfer<br>Augustastraße 6<br>"
                        "40477 Düsseldorf<br>Deutschland</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Kontakt",
                "copy": [("paragraph", f"<p>{_mail_link()}</p>")],
            },
        ),
    ]


def default_privacy_sections():
    """Return the immutable v1 Datenschutz default."""

    return [
        (
            "section",
            {
                "heading": "Verantwortlich",
                "copy": [
                    (
                        "address",
                        "<p>Katharina Wersdörfer<br>Augustastraße 6<br>40477 "
                        f"Düsseldorf<br>Deutschland<br><br>{_mail_link()}</p>",
                    )
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Websiteabruf",
                "copy": [
                    (
                        "paragraph",
                        "<p>Diese Website wird auf einem selbst betriebenen Server "
                        "bereitgestellt. Beim Aufruf verarbeitet der Webserver technisch "
                        "erforderliche Verbindungsdaten. Dazu können insbesondere "
                        "IP-Adresse, Datum und Uhrzeit des Abrufs, aufgerufene Adresse, "
                        "übertragene Datenmenge, Referrer-Adresse sowie Angaben zu "
                        "Browser und Betriebssystem gehören.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Die Verarbeitung ist erforderlich, um die Website auszuliefern, "
                        "ihre Stabilität und Sicherheit zu gewährleisten und technische "
                        "Störungen oder Angriffe nachvollziehen zu können. Rechtsgrundlage "
                        "ist Art. 6 Abs. 1 lit. f DSGVO. Das berechtigte Interesse liegt im "
                        "sicheren und zuverlässigen Betrieb dieser Website.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Server-Logdaten werden spätestens nach sieben Tagen gelöscht, "
                        "sofern ein sicherheitsrelevantes Ereignis nicht ausnahmsweise "
                        "eine längere Aufbewahrung zur Aufklärung erfordert. Die "
                        "Server-Logdaten werden keinem externen Hosting-Dienstleister "
                        "offengelegt.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "E-Mail-Kontakt",
                "copy": [
                    (
                        "paragraph",
                        "<p>Wenn Sie per E-Mail Kontakt aufnehmen, verarbeite ich die von "
                        "Ihnen übermittelten Angaben – insbesondere Name, E-Mail-Adresse, "
                        "Nachrichteninhalt und technische Metadaten – ausschließlich, um "
                        "Ihre Anfrage zu bearbeiten und zu beantworten.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Geht es um eine konkrete Projektanfrage oder eine sonstige "
                        "vorvertragliche Maßnahme, ist Art. 6 Abs. 1 lit. b DSGVO die "
                        "Rechtsgrundlage. Für allgemeine Anfragen erfolgt die Verarbeitung "
                        "nach Art. 6 Abs. 1 lit. f DSGVO; das berechtigte Interesse besteht "
                        "in der sachgerechten Beantwortung Ihrer Nachricht.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Die Daten werden gelöscht, sobald die Anfrage abschließend "
                        "bearbeitet ist und keine gesetzlichen Aufbewahrungspflichten oder "
                        "berechtigten Interessen an einer weiteren Speicherung, "
                        "insbesondere zur Geltendmachung oder Abwehr von Ansprüchen, "
                        "entgegenstehen. Kommt ein Vertrag zustande, können vertrags- und "
                        "steuerrechtlich relevante Unterlagen entsprechend den "
                        "gesetzlichen Aufbewahrungsfristen länger gespeichert werden. "
                        "Empfänger können die für den E-Mail-Verkehr eingesetzten "
                        "Auftragsverarbeiter sein.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Cookies & Tracking",
                "copy": [
                    (
                        "paragraph",
                        "<p>Diese Website setzt keine Cookies ein, speichert keine "
                        "Informationen in Ihrem Endgerät und greift nicht auf dort "
                        "gespeicherte Informationen zu. Es werden keine Analyse-, "
                        "Reichweitenmessungs-, Werbe- oder Profilingdienste verwendet.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Schriften und sonstige Seitenelemente werden lokal "
                        "bereitgestellt. Beim bloßen Besuch der Website werden keine "
                        "Inhalte von Drittanbietern geladen. Daher ist kein "
                        "Einwilligungsbanner erforderlich.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Der E-Mail-Link öffnet lediglich das auf Ihrem Gerät "
                        "eingerichtete E-Mail-Programm. Daten werden erst verarbeitet, "
                        "wenn Sie eine Nachricht absenden.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Empfänger & Drittland",
                "copy": [
                    (
                        "paragraph",
                        "<p>Eine Weitergabe personenbezogener Daten erfolgt nur, soweit sie "
                        "für die genannten Zwecke erforderlich ist, eine gesetzliche "
                        "Verpflichtung besteht oder Sie eingewilligt haben. Beim Versand "
                        "einer E-Mail werden Daten technisch über die jeweils beteiligten "
                        "E-Mail-Anbieter übertragen.</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Eine Übermittlung personenbezogener Daten in Staaten außerhalb "
                        "der Europäischen Union oder des Europäischen Wirtschaftsraums "
                        "durch mich ist nicht vorgesehen.</p>",
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Ihre Rechte",
                "copy": [
                    (
                        "paragraph",
                        "<p>Sie haben nach Maßgabe der gesetzlichen Voraussetzungen das "
                        "Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der "
                        "Verarbeitung und Datenübertragbarkeit. Einer Verarbeitung auf "
                        "Grundlage von Art. 6 Abs. 1 lit. f DSGVO können Sie aus Gründen, "
                        "die sich aus Ihrer besonderen Situation ergeben, widersprechen.</p>",
                    ),
                    (
                        "paragraph",
                        f"<p>{_mail_link('Zur Ausübung Ihrer Rechte genügt eine Nachricht an', '.')}</p>",
                    ),
                    (
                        "paragraph",
                        "<p>Sie haben außerdem das Recht, sich bei einer "
                        "Datenschutzaufsichtsbehörde zu beschweren. Zuständig ist "
                        "insbesondere die Landesbeauftragte für Datenschutz und "
                        "Informationsfreiheit Nordrhein-Westfalen, Kavalleriestraße 2–4, "
                        "40213 Düsseldorf, "
                        '<a href="https://www.ldi.nrw.de/">www.ldi.nrw.de</a>.</p>',
                    ),
                ],
            },
        ),
        (
            "section",
            {
                "heading": "Bereitstellung",
                "copy": [
                    (
                        "paragraph",
                        "<p>Sie sind weder gesetzlich noch vertraglich verpflichtet, "
                        "personenbezogene Daten bereitzustellen. Ohne die für eine E-Mail "
                        "erforderlichen Angaben kann eine Anfrage jedoch nicht beantwortet "
                        "werden. Eine automatisierte Entscheidungsfindung einschließlich "
                        "Profiling findet nicht statt.</p>",
                    ),
                    ("note", "Stand: September 2026"),
                ],
            },
        ),
    ]
