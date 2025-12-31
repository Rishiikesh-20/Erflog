from jinja2 import Template
from weasyprint import HTML, CSS
import os


RESUME_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} - Resume</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        @page {
            size: A4;
            margin: 0.75in;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #1a1a1a;
            background: #ffffff;
        }
        
        .container {
            max-width: 100%;
        }
        
        /* Header Section */
        .header {
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 2px solid #2563eb;
            margin-bottom: 24px;
        }
        
        .name {
            font-size: 28pt;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
        }
        
        .contact-info {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 9pt;
            color: #4b5563;
        }
        
        .contact-item {
            display: inline-block;
        }
        
        .contact-item a {
            color: #2563eb;
            text-decoration: none;
        }
        
        /* Section Styles */
        .section {
            margin-bottom: 20px;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 11pt;
            font-weight: 600;
            color: #2563eb;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 6px;
            margin-bottom: 12px;
        }
        
        /* Summary */
        .summary {
            font-size: 10pt;
            color: #374151;
            line-height: 1.6;
            text-align: justify;
        }
        
        /* Experience & Education Items */
        .item {
            margin-bottom: 16px;
            page-break-inside: avoid;
        }
        
        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 4px;
        }
        
        .item-title {
            font-size: 11pt;
            font-weight: 600;
            color: #111827;
        }
        
        .item-date {
            font-size: 9pt;
            color: #6b7280;
            font-weight: 500;
        }
        
        .item-subtitle {
            font-size: 10pt;
            color: #4b5563;
            font-style: italic;
            margin-bottom: 6px;
        }
        
        .item-bullets {
            list-style: none;
            padding-left: 0;
        }
        
        .item-bullets li {
            position: relative;
            padding-left: 14px;
            margin-bottom: 4px;
            font-size: 9.5pt;
            color: #374151;
            line-height: 1.5;
        }
        
        .item-bullets li::before {
            content: "▸";
            position: absolute;
            left: 0;
            color: #2563eb;
            font-size: 8pt;
        }
        
        /* Skills */
        .skills-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .skill-tag {
            background: #eff6ff;
            color: #1d4ed8;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: 500;
        }
        
        /* Projects */
        .project-name {
            font-weight: 600;
            color: #111827;
        }
        
        .project-tech {
            font-size: 8.5pt;
            color: #6b7280;
            font-style: italic;
        }
        
        /* Certifications */
        .cert-item {
            margin-bottom: 6px;
        }
        
        .cert-name {
            font-weight: 500;
            color: #111827;
        }
        
        .cert-issuer {
            color: #6b7280;
            font-size: 9pt;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1 class="name">{{ name }}</h1>
            <div class="contact-info">
                {% if email %}<span class="contact-item">{{ email }}</span>{% endif %}
                {% if phone %}<span class="contact-item">{{ phone }}</span>{% endif %}
                {% if location %}<span class="contact-item">{{ location }}</span>{% endif %}
                {% if linkedin %}<span class="contact-item"><a href="{{ linkedin }}">LinkedIn</a></span>{% endif %}
                {% if github %}<span class="contact-item"><a href="{{ github }}">GitHub</a></span>{% endif %}
                {% if portfolio %}<span class="contact-item"><a href="{{ portfolio }}">Portfolio</a></span>{% endif %}
            </div>
        </header>
        
        <!-- Summary -->
        {% if summary %}
        <section class="section">
            <h2 class="section-title">Professional Summary</h2>
            <p class="summary">{{ summary }}</p>
        </section>
        {% endif %}
        
        <!-- Experience -->
        {% if experience %}
        <section class="section">
            <h2 class="section-title">Experience</h2>
            {% for job in experience %}
            <div class="item">
                <div class="item-header">
                    <span class="item-title">{{ job.title }}</span>
                    <span class="item-date">{{ job.start_date }} - {{ job.end_date | default('Present') }}</span>
                </div>
                <div class="item-subtitle">{{ job.company }}{% if job.location %} · {{ job.location }}{% endif %}</div>
                {% if job.bullets %}
                <ul class="item-bullets">
                    {% for bullet in job.bullets %}
                    <li>{{ bullet }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </section>
        {% endif %}
        
        <!-- Education -->
        {% if education %}
        <section class="section">
            <h2 class="section-title">Education</h2>
            {% for edu in education %}
            <div class="item">
                <div class="item-header">
                    <span class="item-title">{{ edu.degree }}</span>
                    <span class="item-date">{{ edu.graduation_date | default(edu.end_date) }}</span>
                </div>
                <div class="item-subtitle">{{ edu.institution }}{% if edu.location %} · {{ edu.location }}{% endif %}</div>
                {% if edu.gpa %}<p style="font-size: 9pt; color: #4b5563;">GPA: {{ edu.gpa }}</p>{% endif %}
            </div>
            {% endfor %}
        </section>
        {% endif %}
        
        <!-- Skills -->
        {% if skills %}
        <section class="section">
            <h2 class="section-title">Skills</h2>
            <div class="skills-grid">
                {% for skill in skills %}
                <span class="skill-tag">{{ skill }}</span>
                {% endfor %}
            </div>
        </section>
        {% endif %}
        
        <!-- Projects -->
        {% if projects %}
        <section class="section">
            <h2 class="section-title">Projects</h2>
            {% for project in projects %}
            <div class="item">
                <div class="item-header">
                    <span class="project-name">{{ project.name }}</span>
                    {% if project.date %}<span class="item-date">{{ project.date }}</span>{% endif %}
                </div>
                {% if project.technologies %}<p class="project-tech">{{ project.technologies | join(', ') }}</p>{% endif %}
                {% if project.description %}<p style="font-size: 9.5pt; color: #374151; margin-top: 4px;">{{ project.description }}</p>{% endif %}
                {% if project.bullets %}
                <ul class="item-bullets">
                    {% for bullet in project.bullets %}
                    <li>{{ bullet }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </section>
        {% endif %}
        
        <!-- Certifications -->
        {% if certifications %}
        <section class="section">
            <h2 class="section-title">Certifications</h2>
            {% for cert in certifications %}
            <div class="cert-item">
                <span class="cert-name">{{ cert.name }}</span>
                {% if cert.issuer %}<span class="cert-issuer"> · {{ cert.issuer }}</span>{% endif %}
                {% if cert.date %}<span class="cert-issuer"> ({{ cert.date }})</span>{% endif %}
            </div>
            {% endfor %}
        </section>
        {% endif %}
    </div>
</body>
</html>
"""


def generate_pdf(resume_data: dict, output_path: str) -> str:
    """
    Generates a PDF resume from structured resume data.
    
    Args:
        resume_data: Dictionary containing resume information.
        output_path: File path where the PDF will be saved.
    
    Returns:
        The output file path.
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Render the Jinja2 template
    template = Template(RESUME_TEMPLATE)
    rendered_html = template.render(**resume_data)
    
    # Convert HTML to PDF using WeasyPrint
    html_doc = HTML(string=rendered_html)
    html_doc.write_pdf(output_path)
    
    return output_path
