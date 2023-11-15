from functools import lru_cache
from typing import Dict, List
import re
import pandas as pd
from rich import print
from rich.console import Group, Text
from rich.panel import Panel

from edgar._rich import repr_rich
from edgar.financials import Financials
from edgar.htmltools import ChunkedDocument

__all__ = [
    'TenK',
    'TenQ',
    'TwentyF',
    'is_valid_item_for_filing'
]


class CompanyReport:

    def __init__(self, filing):
        self._filing = filing

    @property
    def form(self):
        return self._filing.form

    @property
    def company(self):
        return self._filing.company

    @property
    def income_statement(self):
        return self.financials.income_statement if self.financials else None

    @property
    def balance_sheet(self):
        return self.financials.balance_sheet if self.financials else None

    @property
    def cash_flow_statement(self):
        return self.financials.cash_flow_statement if self.financials else None

    @property
    @lru_cache(1)
    def financials(self):
        xbrl = self._filing.xbrl()
        if xbrl:
            return Financials.from_gaap(xbrl.gaap)

    @property
    @lru_cache(maxsize=1)
    def chunked_document(self):
        return ChunkedDocument(self._filing.html())

    @property
    def doc(self):
        return self.chunked_document

    def view(self, item_or_part: str):
        """Get the Item or Part from the filing document. e.g. Item 1 Business from 10-K or Part I from 10-Q"""
        item_text = self[item_or_part]
        if item_text:
            print(item_text)

    def __getitem__(self, item_or_part: str):
        # Show the item or part from the filing document. e.g. Item 1 Business from 10-K or Part I from 10-Q
        item_text = self.chunked_document[item_or_part]
        return item_text

    def __rich__(self):
        return Panel(
            Group(
                self._filing.__rich__(),
                self.financials or Text("No financial data available")
            )
        )

    def __repr__(self):
        return repr_rich(self.__rich__())


class TenK(CompanyReport):
    structure = {
        "PART I": {
            "ITEM 1": "Business: Overview of the company's business operations, products, services, and market environment.",
            "ITEM 1A": "Risk Factors: Discussion of risks and uncertainties that could materially affect the company's financial condition or results of operations.",
            "ITEM 1B": "Unresolved Staff Comments: Any comments from the SEC staff on the company’s previous filings that remain unresolved.",
            "ITEM 2": "Properties: Information about the physical properties owned or leased by the company.",
            "ITEM 3": "Legal Proceedings: Details of significant ongoing legal proceedings.",
            "ITEM 4": "Mine Safety Disclosures: Relevant for mining companies, disclosures about mine safety and regulatory compliance."
        },
        "PART II": {
            "ITEM 5": "Market for Registrant’s Common Equity: Information on the company’s equity, including stock performance and shareholder matters.",
            "ITEM 6": "Selected Financial Data: Financial data summary for the last five fiscal years.",
            "ITEM 7": "Management’s Discussion and Analysis (MD&A): Management’s perspective on the financial condition, changes in financial condition, and results of operations.",
            "ITEM 7A": "Quantitative and Qualitative Disclosures About Market Risk: Information on the company's exposure to market risk.",
            "ITEM 8": "Financial Statements: Complete audited financial statements.",
            "ITEM 9": "Controls and Procedures: Evaluation of the effectiveness of the company’s disclosure controls and procedures.",
            "ITEM 9A": "Controls and Procedures: Evaluation of internal controls over financial reporting.",
            "ITEM 9B": "Other Information: Any other relevant information not covered in other sections."
        },
        "PART III": {
            "ITEM 10": "Directors, Executive Officers, and Corporate Governance: Information about the company's directors, executive officers, and governance policies.",
            "ITEM 11": "Executive Compensation: Details of compensation paid to key executives.",
            "ITEM 12": "Security Ownership of Certain Beneficial Owners and Management: Information about stock ownership.",
            "ITEM 13": "Certain Relationships and Related Transactions, and Director Independence: Information on transactions between the company and its directors, officers, and significant shareholders.",
            "ITEM 14": "Principal Accounting Fees and Services: Fees paid to the principal accountant and services rendered."
        },
        "PART IV": {
            "ITEM 15": "Exhibits, Financial Statement Schedules: Legal documents and financial schedules that support the financial statements and disclosures."
        }
    }

    def __init__(self, filing):
        assert filing.form in ['10-K', '10-K/A'], f"This form should be a 10-K but was {filing.form}"
        super().__init__(filing)

    def __str__(self):
        return f"""TenK('{self.company}')"""


class TenQ(CompanyReport):
    structure = {
        "PART I": {  # Financial Information
            "ITEM 1": "Financial Statements: Unaudited financial statements including balance sheets, income statements, and cash flow statements.",
            "ITEM 2": "Management’s Discussion and Analysis of Financial Condition and Results of Operations (MD&A): Management’s perspective on the financial condition and results of operations.",
            "ITEM 3": "Quantitative and Qualitative Disclosures About Market Risk: Information on the company's exposure to market risk.",
            "ITEM 4": "Controls and Procedures: Evaluation of the effectiveness of disclosure controls and procedures."
        },
        "PART II": {  # Other Information
            "ITEM 1": "Legal Proceedings: Brief description of any significant pending legal proceedings.",
            "ITEM 1A": "Risk Factors: An update on risk factors that may affect future results.",
            "ITEM 2": "Unregistered Sales of Equity Securities and Use of Proceeds: Details of unregistered sales of equity securities.",
            "ITEM 3": "Defaults Upon Senior Securities: Information regarding any defaults on senior securities.",
            "ITEM 4": "Mine Safety Disclosures: Required for companies with mining operations.",
            "ITEM 5": "Other Information: Any other information that should be disclosed to investors.",
            "ITEM 6": "Exhibits: List of exhibits required by ITEM 601 of Regulation S-K."
        }
    }

    def __init__(self, filing):
        assert filing.form in ['10-Q', '10-Q/A'], f"This form should be a 10-Q but was {filing.form}"
        super().__init__(filing)

    def __str__(self):
        return f"""TenQ('{self.company}')"""


class TwentyF(CompanyReport):
    structure = {
        "PART I": {
            "ITEM 1": "Identity of Directors, Senior Management, and Advisers: Information about the company's directors, senior management, and advisers.",
            "ITEM 2": "Offer Statistics and Expected Timetable: Details on recent and expected offers of securities.",
            "ITEM 3": "Key Information: Financial and other key information about the company, including risk factors and ratios.",
            "ITEM 4": "Information on the Company: Detailed information about the company's operations and properties.",
            "ITEM 4A": "Unresolved Staff Comments: Any comments from the SEC staff on the company’s previous filings that remain unresolved."
        },
        "PART II": {
            "ITEM 5": "Operating and Financial Review and Prospects: Management’s discussion and analysis of financial condition and results of operations.",
            "ITEM 6": "Directors, Senior Management, and Employees: Information about the company's directors, senior management, and employees.",
            "ITEM 7": "Major Shareholders and Related PARTy Transactions: Information about major shareholders and transactions with related parties.",
            "ITEM 8": "Financial Information: Audited financial statements and supplementary financial information.",
            "ITEM 9": "The Offer and Listing: Details on the company's securities and markets where they are traded."
        },
        "PART III": {
            "ITEM 10": "Additional Information: Additional information such as share capital, memoranda, and articles of association.",
            "ITEM 11": "Quantitative and Qualitative Disclosures About Market Risk: Information on the company's exposure to market risk.",
            "ITEM 12": "Description of Securities Other Than Equity Securities: Detailed information on securities other than equity."
        },
        "PART IV": {
            "ITEM 13": "Defaults, Dividend Arrearages, and Delinquencies: Information about defaults on payments and arrearages.",
            "ITEM 14": "Material Modifications to the Rights of Security Holders and Use of Proceeds: Details on any modifications to the rights of security holders.",
            "ITEM 15": "Controls and Procedures: Assessment of the effectiveness of disclosure controls and internal controls over financial reporting.",
            "ITEM 16": ["16A. Audit Committee Financial Expert", "16B. Code of Ethics",
                        "16C. Principal Accountant Fees and Services",
                        "16D. Exemptions from the Listing Standards for Audit Committees",
                        "16E. Purchases of Equity Securities by the Issuer and Affiliated Purchasers",
                        "16F. Change in Registrant’s Certifying Accountant", "16G. Corporate Governance"]
        },
        "PART V": {
            "ITEM 17": "Financial Statements: Financial statements prepared in accordance with or reconciled to U.S. GAAP or IFRS.",
            "ITEM 18": "Financial Statements: If different from ITEM 17, financial statements prepared in accordance with home country standards.",
            "ITEM 19": "Exhibits: Legal and financial documents supporting the information in the report."
        }
    }

    def __init__(self, filing):
        assert filing.form in ['20-F', '20-F/A'], f"This form should be a 20-F but was {filing.form}"
        super().__init__(filing)

    def __str__(self):
        return f"""TwentyF('{self.company}')"""


def is_valid_item_for_filing(filing_structure: Dict, item: str, part: str = None):
    """Return true if the item is valid"""
    if part:
        return item.upper() in filing_structure[part.upper()]
    else:
        for part in filing_structure.keys():
            if item.upper() in filing_structure[part]:
                return True
    return False