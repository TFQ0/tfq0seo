"""Export analysis results in multiple formats."""

import json
import csv
import yaml
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

class BaseExporter:
    """Base class for exporters."""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize exporter."""
        self.data = data
        self.timestamp = datetime.now().isoformat()
    
    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = '',
        sep: str = '_'
    ) -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(
                    self._flatten_dict(v, new_key, sep=sep).items()
                )
            elif isinstance(v, list):
                if v and isinstance(v[0], dict):
                    # Handle list of dictionaries
                    for i, item in enumerate(v):
                        items.extend(
                            self._flatten_dict(
                                item,
                                f"{new_key}{sep}{i}",
                                sep=sep
                            ).items()
                        )
                else:
                    items.append((new_key, v))
            else:
                items.append((new_key, v))
        return dict(items)

class JSONExporter(BaseExporter):
    """Export data in JSON format."""
    
    def export(
        self,
        output_path: str,
        pretty: bool = True
    ) -> None:
        """Export data to JSON file."""
        data = {
            "data": self.data,
            "metadata": {
                "timestamp": self.timestamp,
                "format": "json"
            }
        }
        
        with open(output_path, 'w') as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)

class CSVExporter(BaseExporter):
    """Export data in CSV format."""
    
    def export(
        self,
        output_path: str,
        flatten: bool = True
    ) -> None:
        """Export data to CSV file."""
        if flatten:
            data = self._flatten_dict(self.data)
        else:
            data = self.data
        
        df = pd.DataFrame([data])
        df['timestamp'] = self.timestamp
        df.to_csv(output_path, index=False)

class ExcelExporter(BaseExporter):
    """Export data in Excel format."""
    
    def export(
        self,
        output_path: str,
        sheets: Optional[Dict[str, List[str]]] = None
    ) -> None:
        """Export data to Excel file."""
        writer = pd.ExcelWriter(output_path, engine='openpyxl')
        
        if sheets:
            # Export specific data to sheets
            for sheet_name, fields in sheets.items():
                sheet_data = {
                    k: v for k, v in self.data.items()
                    if k in fields
                }
                df = pd.DataFrame([sheet_data])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            # Export all data to single sheet
            df = pd.DataFrame([self._flatten_dict(self.data)])
            df['timestamp'] = self.timestamp
            df.to_excel(writer, sheet_name='Analysis Results', index=False)
        
        writer.save()

class XMLExporter(BaseExporter):
    """Export data in XML format."""
    
    def export(self, output_path: str) -> None:
        """Export data to XML file."""
        root = ET.Element("analysis_results")
        
        # Add metadata
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "timestamp").text = self.timestamp
        ET.SubElement(metadata, "format").text = "xml"
        
        # Add data
        data_elem = ET.SubElement(root, "data")
        self._dict_to_xml(self.data, data_elem)
        
        # Write to file
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    def _dict_to_xml(
        self,
        d: Dict[str, Any],
        parent: ET.Element
    ) -> None:
        """Convert dictionary to XML elements."""
        for key, value in d.items():
            elem = ET.SubElement(parent, key)
            
            if isinstance(value, dict):
                self._dict_to_xml(value, elem)
            elif isinstance(value, list):
                for item in value:
                    item_elem = ET.SubElement(elem, "item")
                    if isinstance(item, dict):
                        self._dict_to_xml(item, item_elem)
                    else:
                        item_elem.text = str(item)
            else:
                elem.text = str(value)

class YAMLExporter(BaseExporter):
    """Export data in YAML format."""
    
    def export(self, output_path: str) -> None:
        """Export data to YAML file."""
        data = {
            "data": self.data,
            "metadata": {
                "timestamp": self.timestamp,
                "format": "yaml"
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

class HTMLExporter(BaseExporter):
    """Export data as HTML report."""
    
    def export(
        self,
        output_path: str,
        template_path: Optional[str] = None
    ) -> None:
        """Export data to HTML file."""
        if template_path:
            with open(template_path, 'r') as f:
                template = f.read()
        else:
            template = self._get_default_template()
        
        # Generate visualizations
        charts = self._generate_charts()
        
        # Prepare data for template
        context = {
            "data": self.data,
            "charts": charts,
            "timestamp": self.timestamp
        }
        
        # Render template
        html = template.format(**context)
        
        with open(output_path, 'w') as f:
            f.write(html)
    
    def _get_default_template(self) -> str:
        """Get default HTML template."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SEO Analysis Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .section {
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #f5f5f5;
                    border-radius: 5px;
                }
                .chart {
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>SEO Analysis Report</h1>
                <p>Generated: {timestamp}</p>
                
                {charts}
                
                <div class="section">
                    <h2>Raw Data</h2>
                    <pre>{data}</pre>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_charts(self) -> str:
        """Generate Plotly charts for visualization."""
        charts = []
        
        # Example charts - customize based on data structure
        if 'keyword_analysis' in self.data:
            kw_data = self.data['keyword_analysis']
            if 'volume_trends' in kw_data:
                fig = go.Figure(
                    data=[
                        go.Scatter(
                            x=list(range(len(kw_data['volume_trends']))),
                            y=kw_data['volume_trends'],
                            mode='lines+markers'
                        )
                    ]
                )
                fig.update_layout(
                    title="Keyword Volume Trends",
                    xaxis_title="Time",
                    yaxis_title="Search Volume"
                )
                charts.append(fig.to_html(full_html=False))
        
        if 'backlink_analysis' in self.data:
            bl_data = self.data['backlink_analysis']
            if 'domain_authority_dist' in bl_data:
                fig = px.histogram(
                    x=bl_data['domain_authority_dist'],
                    title="Domain Authority Distribution"
                )
                charts.append(fig.to_html(full_html=False))
        
        return "\n".join(
            f'<div class="chart">{chart}</div>'
            for chart in charts
        )

class MarkdownExporter(BaseExporter):
    """Export data in Markdown format."""
    
    def export(self, output_path: str) -> None:
        """Export data to Markdown file."""
        md = f"""# SEO Analysis Report

Generated: {self.timestamp}

"""
        md += self._dict_to_md(self.data)
        
        with open(output_path, 'w') as f:
            f.write(md)
    
    def _dict_to_md(
        self,
        d: Dict[str, Any],
        level: int = 2
    ) -> str:
        """Convert dictionary to Markdown format."""
        md = ""
        
        for key, value in d.items():
            md += f"{'#' * level} {key}\n\n"
            
            if isinstance(value, dict):
                md += self._dict_to_md(value, level + 1)
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    for item in value:
                        md += self._dict_to_md(item, level + 1)
                else:
                    md += "- " + "\n- ".join(str(item) for item in value)
                    md += "\n\n"
            else:
                md += f"{value}\n\n"
        
        return md

def export_results(
    data: Dict[str, Any],
    format: str,
    output_path: str,
    **kwargs: Any
) -> None:
    """Export analysis results in specified format."""
    exporters = {
        'json': JSONExporter,
        'csv': CSVExporter,
        'excel': ExcelExporter,
        'xml': XMLExporter,
        'yaml': YAMLExporter,
        'html': HTMLExporter,
        'md': MarkdownExporter
    }
    
    if format not in exporters:
        raise ValueError(
            f"Unsupported format: {format}. "
            f"Supported formats: {', '.join(exporters.keys())}"
        )
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export data
    exporter = exporters[format](data)
    exporter.export(output_path, **kwargs) 