#!/usr/bin/env python3
"""
Cybersecurity Certification Roadmap PDF Generator
Generates a comprehensive, professional PDF roadmap with QR codes and resource mappings
"""

import json
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfgen import canvas
import qrcode
from io import BytesIO


class RoadmapGenerator:
    """Main class for generating the cybersecurity roadmap PDF"""
    
    def __init__(self, output_dir="output"):
        """Initialize the generator with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.data_dir = Path("data")
        
        # Load all data
        self.certifications = self._load_json("certifications.json")
        self.youtube_channels = self._load_json("youtube_channels.json")
        self.labs = self._load_json("labs.json")
        self.tools = self._load_json("tools.json")
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Story elements (content of PDF)
        self.story = []
        
        # Stage colors
        self.stage_colors = {
            0: colors.HexColor("#1a1a1a"),  # Black - Absolute Zero
            1: colors.HexColor("#00ff00"),  # Green - Beginner
            2: colors.HexColor("#00aa00"),  # Dark Green - Junior
            3: colors.HexColor("#0088ff"),  # Blue - Real Pentester
            4: colors.HexColor("#ff8800"),  # Orange - OSCP
            5: colors.HexColor("#ff0088"),  # Pink - CPTS
            6: colors.HexColor("#ff0000"),  # Red - Red Team
            7: colors.HexColor("#8800ff"),  # Purple - Web God
            8: colors.HexColor("#0088aa"),  # Cyan - Defensive
            9: colors.HexColor("#ffaa00"),  # Yellow-Orange - Wireless
            10: colors.HexColor("#aa0088"),  # Magenta - Exploit Dev
            11: colors.HexColor("#880000"),  # Dark Red - Exploit Elite
            12: colors.HexColor("#ffffff"),  # White - macOS
        }
        
    def _load_json(self, filename):
        """Load JSON data file"""
        filepath = self.data_dir / filename
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=36,
            textColor=colors.HexColor("#00ff00"),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Stage title
        self.styles.add(ParagraphStyle(
            name='StageTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#00ff00"),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor("#00aaff"),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Subsection
        self.styles.add(ParagraphStyle(
            name='SubSection',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor("#ffffff"),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
        
        # List style
        self.styles.add(ParagraphStyle(
            name='ListItem',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            leftIndent=20,
            spaceAfter=3
        ))
    
    def _create_qr_code(self, data, size=1.5*inch):
        """Create QR code image from data"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Create ReportLab image
        return Image(buffer, width=size, height=size)
    
    def _add_cover_page(self):
        """Add cover page to the document"""
        # Title
        title = Paragraph(
            "Cybersecurity Certification Roadmap",
            self.styles['CustomTitle']
        )
        self.story.append(title)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        subtitle = Paragraph(
            "A Comprehensive Guide from Zero to Expert",
            self.styles['Heading2']
        )
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.3*inch))
        
        # Overview
        overview_text = """
        This roadmap provides a structured path through the world of cybersecurity,
        from absolute beginner to expert-level certifications. It covers 13 stages
        (Stage 0 through Stage 12) and maps out the resources, tools, labs, and
        YouTube channels you'll need at each level.
        """
        overview = Paragraph(overview_text, self.styles['CustomBody'])
        self.story.append(overview)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Key stats
        stats_data = [
            ['Metric', 'Count'],
            ['Total Stages', '13 (0-12)'],
            ['Certifications Covered', '12'],
            ['YouTube Channels', f'{self._count_youtube_channels()}'],
            ['Practice Labs', f'{self._count_labs()}'],
            ['Tools & Frameworks', f'{self._count_tools()}'],
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#00ff00")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        self.story.append(stats_table)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Date
        date_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        date = Paragraph(date_text, self.styles['Normal'])
        self.story.append(date)
        
        # Page break
        self.story.append(PageBreak())
    
    def _count_youtube_channels(self):
        """Count total YouTube channels"""
        count = 0
        for category in self.youtube_channels.values():
            count += len(category)
        return count
    
    def _count_labs(self):
        """Count total lab platforms"""
        count = 0
        for stage_labs in self.labs.values():
            count += len(stage_labs)
        return count
    
    def _count_tools(self):
        """Count total tools"""
        count = 0
        for tool_category in self.tools.values():
            count += len(tool_category)
        return count
    
    def _add_table_of_contents(self):
        """Add table of contents"""
        toc_title = Paragraph("Table of Contents", self.styles['StageTitle'])
        self.story.append(toc_title)
        self.story.append(Spacer(1, 0.2*inch))
        
        toc_items = [
            "1. Foundation Knowledge",
            "2. Stage 0: Absolute Zero",
            "3. Stage 1: Beginner Hacker",
            "4. Stage 2: Junior Pentester Level",
            "5. Stage 3: Real Pentester",
            "6. Stage 4: OSCP Level",
            "7. Stage 5: Complete Pentester (CPTS)",
            "8. Stage 6: Red Team/Evasion (OSEP)",
            "9. Stage 7: Web God Level (OSWE)",
            "10. Stage 8: Defensive Mindset (OSDA)",
            "11. Stage 9: Wireless Specialist (OSWP)",
            "12. Stage 10: Exploit Development (OSED)",
            "13. Stage 11: Exploit Elite (OSEE)",
            "14. Stage 12: macOS Researcher (OSMR)",
            "15. Complete Tool Reference",
            "16. YouTube Channel Directory",
            "17. Resource Links",
        ]
        
        for item in toc_items:
            toc_item = Paragraph(f"• {item}", self.styles['ListItem'])
            self.story.append(toc_item)
        
        self.story.append(PageBreak())
    
    def _add_foundation_section(self):
        """Add foundation knowledge section"""
        title = Paragraph("Foundation Knowledge", self.styles['StageTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))
        
        intro = Paragraph(
            """Before diving into cybersecurity certifications, it's crucial to build
            a solid foundation. This section covers the essential prerequisites and
            foundational resources.""",
            self.styles['CustomBody']
        )
        self.story.append(intro)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Foundation channels
        channels_heading = Paragraph("Foundation YouTube Channels", self.styles['SectionHeading'])
        self.story.append(channels_heading)
        
        if 'foundation' in self.youtube_channels:
            for channel in self.youtube_channels['foundation']:
                channel_name = f"<b>{channel['name']}</b>"
                channel_desc = f"{channel['description']}"
                channel_url = f"<link href='{channel['url']}'>{channel['url']}</link>"
                
                channel_para = Paragraph(
                    f"{channel_name}: {channel_desc}<br/>{channel_url}",
                    self.styles['CustomBody']
                )
                self.story.append(channel_para)
                self.story.append(Spacer(1, 0.1*inch))
        
        self.story.append(PageBreak())
    
    def _add_stage(self, stage_num, stage_name, description, certifications_list=None):
        """Add a complete stage section"""
        # Stage title with color
        stage_color = self.stage_colors.get(stage_num, colors.green)
        
        title_text = f"Stage {stage_num}: {stage_name}"
        title = Paragraph(title_text, self.styles['StageTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Description
        desc = Paragraph(description, self.styles['CustomBody'])
        self.story.append(desc)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Certifications for this stage
        if certifications_list:
            cert_heading = Paragraph("Certifications", self.styles['SectionHeading'])
            self.story.append(cert_heading)
            
            for cert in certifications_list:
                cert_data = self._find_certification(cert)
                if cert_data:
                    cert_text = f"""
                    <b>{cert_data.get('full_name', cert)}</b> ({cert_data.get('name', cert)})<br/>
                    {cert_data.get('description', '')}<br/>
                    <i>Difficulty:</i> {cert_data.get('difficulty', 'N/A')} | 
                    <i>Est. Time:</i> {cert_data.get('estimated_time', 'N/A')}<br/>
                    <link href='{cert_data.get('url', '#')}'>{cert_data.get('url', 'No URL')}</link>
                    """
                    cert_para = Paragraph(cert_text, self.styles['CustomBody'])
                    self.story.append(cert_para)
                    self.story.append(Spacer(1, 0.15*inch))
        
        # YouTube channels for this stage
        stage_channels = self._get_channels_for_stage(stage_num)
        if stage_channels:
            yt_heading = Paragraph("YouTube Channels", self.styles['SectionHeading'])
            self.story.append(yt_heading)
            
            for channel in stage_channels[:5]:  # Limit to top 5 per stage
                channel_text = f"""
                <b>{channel['name']}</b><br/>
                {channel.get('description', '')}<br/>
                <link href='{channel['url']}'>{channel['url']}</link>
                """
                channel_para = Paragraph(channel_text, self.styles['CustomBody'])
                self.story.append(channel_para)
                self.story.append(Spacer(1, 0.1*inch))
        
        # Labs for this stage
        stage_key = f"stage_{stage_num}"
        if stage_key in self.labs:
            labs_heading = Paragraph("Practice Labs & Platforms", self.styles['SectionHeading'])
            self.story.append(labs_heading)
            
            for lab in self.labs[stage_key]:
                lab_text = f"""
                <b>{lab['name']}</b><br/>
                {lab.get('description', '')}<br/>
                <i>Difficulty:</i> {lab.get('difficulty', 'N/A')}<br/>
                <link href='{lab['url']}'>{lab['url']}</link>
                """
                lab_para = Paragraph(lab_text, self.styles['CustomBody'])
                self.story.append(lab_para)
                self.story.append(Spacer(1, 0.1*inch))
        
        # Tools for this stage
        stage_tools = self._get_tools_for_stage(stage_num)
        if stage_tools:
            tools_heading = Paragraph("Essential Tools", self.styles['SectionHeading'])
            self.story.append(tools_heading)
            
            # Create table of tools
            tools_data = [['Tool', 'Description', 'Category']]
            for tool_info in stage_tools[:10]:  # Limit to 10 tools per stage
                tools_data.append([
                    tool_info['name'],
                    tool_info['description'][:50] + '...' if len(tool_info['description']) > 50 else tool_info['description'],
                    tool_info['category']
                ])
            
            if len(tools_data) > 1:
                tools_table = Table(tools_data, colWidths=[1.5*inch, 3*inch, 1.5*inch])
                tools_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                self.story.append(tools_table)
        
        self.story.append(PageBreak())
    
    def _find_certification(self, cert_name):
        """Find certification details by name"""
        for category in self.certifications.values():
            for cert in category:
                if cert['name'] == cert_name or cert.get('full_name') == cert_name:
                    return cert
        return None
    
    def _get_channels_for_stage(self, stage_num):
        """Get YouTube channels relevant to a stage"""
        channels = []
        for category in self.youtube_channels.values():
            for channel in category:
                if 'stages' in channel and stage_num in channel['stages']:
                    channels.append(channel)
        return channels
    
    def _get_tools_for_stage(self, stage_num):
        """Get tools relevant to a stage"""
        tools = []
        for category_name, tool_list in self.tools.items():
            for tool in tool_list:
                if 'stages' in tool and stage_num in tool['stages']:
                    tool_copy = tool.copy()
                    tool_copy['category'] = category_name.replace('_', ' ').title()
                    tools.append(tool_copy)
        return tools
    
    def _add_tool_reference(self):
        """Add complete tool reference section"""
        title = Paragraph("Complete Tool Reference", self.styles['StageTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))
        
        for category_name, tool_list in self.tools.items():
            category_title = category_name.replace('_', ' ').title()
            cat_heading = Paragraph(category_title, self.styles['SectionHeading'])
            self.story.append(cat_heading)
            
            for tool in tool_list:
                tool_text = f"""
                <b>{tool['name']}</b>: {tool['description']}<br/>
                <i>Used in stages:</i> {', '.join(map(str, tool.get('stages', [])))}
                """
                tool_para = Paragraph(tool_text, self.styles['CustomBody'])
                self.story.append(tool_para)
                self.story.append(Spacer(1, 0.05*inch))
            
            self.story.append(Spacer(1, 0.15*inch))
        
        self.story.append(PageBreak())
    
    def _add_youtube_directory(self):
        """Add YouTube channel directory"""
        title = Paragraph("YouTube Channel Directory", self.styles['StageTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))
        
        for category_name, channel_list in self.youtube_channels.items():
            category_title = category_name.replace('_', ' ').title()
            cat_heading = Paragraph(category_title, self.styles['SectionHeading'])
            self.story.append(cat_heading)
            
            for channel in channel_list:
                channel_text = f"""
                <b>{channel['name']}</b><br/>
                {channel.get('description', '')}<br/>
                <link href='{channel['url']}'>{channel['url']}</link>
                """
                channel_para = Paragraph(channel_text, self.styles['CustomBody'])
                self.story.append(channel_para)
                
                # Add QR code for channel
                try:
                    qr_img = self._create_qr_code(channel['url'], size=0.8*inch)
                    self.story.append(qr_img)
                except Exception as e:
                    print(f"Warning: Could not create QR code for {channel['name']}: {e}")
                
                self.story.append(Spacer(1, 0.15*inch))
            
            self.story.append(Spacer(1, 0.2*inch))
        
        self.story.append(PageBreak())
    
    def _add_resource_links(self):
        """Add resource links page"""
        title = Paragraph("Quick Resource Links", self.styles['StageTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))
        
        resources = [
            ("TryHackMe", "https://tryhackme.com"),
            ("Hack The Box", "https://www.hackthebox.com"),
            ("Offensive Security", "https://www.offensive-security.com"),
            ("PortSwigger Academy", "https://portswigger.net/web-security"),
            ("OverTheWire", "https://overthewire.org"),
            ("Exploit-DB", "https://www.exploit-db.com"),
            ("PicoCTF", "https://picoctf.org"),
            ("TCM Security", "https://tcm-sec.com"),
        ]
        
        for name, url in resources:
            resource_text = f"""
            <b>{name}</b><br/>
            <link href='{url}'>{url}</link>
            """
            resource_para = Paragraph(resource_text, self.styles['CustomBody'])
            self.story.append(resource_para)
            self.story.append(Spacer(1, 0.1*inch))
        
        self.story.append(PageBreak())
    
    def _add_easter_egg(self):
        """Add rickroll easter egg QR code"""
        title = Paragraph("Bonus: Secret Resource", self.styles['SectionHeading'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))
        
        easter_egg_text = Paragraph(
            "Scan this QR code for a special motivational resource!",
            self.styles['CustomBody']
        )
        self.story.append(easter_egg_text)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Rickroll QR code
        rickroll_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        try:
            qr_img = self._create_qr_code(rickroll_url, size=2*inch)
            self.story.append(qr_img)
        except Exception as e:
            print(f"Warning: Could not create easter egg QR code: {e}")
        
        self.story.append(Spacer(1, 0.2*inch))
        hint = Paragraph(
            "<i>Hint: This will definitely help you stay motivated during your studies!</i>",
            self.styles['CustomBody']
        )
        self.story.append(hint)
    
    def generate(self, filename="cybersecurity_roadmap.pdf"):
        """Generate the complete PDF"""
        output_path = self.output_dir / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        print("Generating cover page...")
        self._add_cover_page()
        
        print("Generating table of contents...")
        self._add_table_of_contents()
        
        print("Generating foundation section...")
        self._add_foundation_section()
        
        print("Generating stage sections...")
        
        # Stage definitions
        stages = [
            (0, "Absolute Zero", "No IT background required. Start your journey here.", None),
            (1, "Beginner Hacker", "Foundation level - build your core skills.", ["THM JR", "eJPT", "CEH"]),
            (2, "Junior Pentester Level", "Develop practical pentesting skills.", None),
            (3, "Real Pentester", "Industry-ready professional skills.", ["PNPT"]),
            (4, "OSCP Level", "Industry standard certification level.", ["OSCP"]),
            (5, "Complete Pentester", "Advanced comprehensive pentesting.", ["CPTS"]),
            (6, "Red Team/Evasion", "Advanced red team operations.", ["OSEP"]),
            (7, "Web God Level", "Expert web application security.", ["OSWE"]),
            (8, "Defensive Mindset", "Blue team and defensive security.", ["OSDA"]),
            (9, "Wireless Specialist", "Wireless network security expert.", ["OSWP"]),
            (10, "Exploit Development", "Binary exploitation fundamentals.", ["OSED"]),
            (11, "Exploit Elite", "Advanced exploit development.", ["OSEE"]),
            (12, "macOS Researcher", "macOS security research specialist.", ["OSMR"]),
        ]
        
        for stage_num, stage_name, description, certs in stages:
            print(f"  - Stage {stage_num}: {stage_name}")
            self._add_stage(stage_num, stage_name, description, certs)
        
        print("Generating tool reference...")
        self._add_tool_reference()
        
        print("Generating YouTube directory...")
        self._add_youtube_directory()
        
        print("Generating resource links...")
        self._add_resource_links()
        
        print("Adding easter egg...")
        self._add_easter_egg()
        
        # Build PDF
        print(f"Building PDF: {output_path}")
        doc.build(self.story)
        
        print(f"✓ PDF generated successfully: {output_path}")
        print(f"  File size: {output_path.stat().st_size / 1024:.2f} KB")
        
        return output_path


def main():
    """Main entry point"""
    print("=" * 60)
    print("Cybersecurity Certification Roadmap Generator")
    print("=" * 60)
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Create generator
    generator = RoadmapGenerator()
    
    # Generate PDF
    output_file = generator.generate()
    
    print()
    print("=" * 60)
    print("Generation complete!")
    print(f"Output: {output_file.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
