"""
内部数据库基本面数据获取

通过 TransMatrix 内部数据库获取 A 股基本面原始数据，
返回格式化字符串供 LLM 分析。

  - get_fundamentals_overview  -> 公司概览 + 估值 + 关键指标
  - get_balance_sheet_data     -> 资产负债表原始数据
  - get_cashflow_data          -> 现金流量表原始数据
  - get_income_statement_data  -> 利润表原始数据
"""

from datetime import datetime
from typing import Optional

import pandas as pd

import logging
logger = logging.getLogger(__name__)


# ==================== 字段中文映射 ====================

BALANCE_FIELD_ZH = {
    "cash_equivalents": "货币资金",
    "trading_assets": "交易性金融资产",
    "bill_receivable": "应收票据",
    "account_receivable": "应收账款",
    "advance_payment": "预付款项",
    "interest_receivable": "应收利息",
    "dividend_receivable": "应收股利",
    "other_receivable": "其他应收款",
    "inventories": "存货",
    "non_current_asset_in_one_year": "一年内到期的非流动资产",
    "other_current_assets": "其他流动资产",
    "total_current_assets": "流动资产合计",
    "hold_for_sale_assets": "可供出售金融资产",
    "longterm_equity_invest": "长期股权投资",
    "investment_property": "投资性房地产",
    "fixed_assets": "固定资产",
    "constru_in_process": "在建工程",
    "intangible_assets": "无形资产",
    "development_expenditure": "开发支出",
    "good_will": "商誉",
    "long_deferred_expense": "长期待摊费用",
    "deferred_tax_assets": "递延所得税资产",
    "other_non_current_assets": "其他非流动资产",
    "total_non_current_assets": "非流动资产合计",
    "total_assets": "资产总计",
    "shortterm_loan": "短期借款",
    "trading_liability": "交易性金融负债",
    "notes_payable": "应付票据",
    "accounts_payable": "应付账款",
    "advance_peceipts": "预收款项",
    "salaries_payable": "应付职工薪酬",
    "taxs_payable": "应交税费",
    "interest_payable": "应付利息",
    "dividend_payable": "应付股利",
    "other_payable": "其他应付款",
    "non_current_liability_in_one_year": "一年内到期的非流动负债",
    "other_current_liability": "其他流动负债",
    "total_current_liability": "流动负债合计",
    "longterm_loan": "长期借款",
    "bonds_payable": "应付债券",
    "longterm_account_payable": "长期应付款",
    "estimate_liability": "预计负债",
    "deferred_tax_liability": "递延所得税负债",
    "other_non_current_liability": "其他非流动负债",
    "total_non_current_liability": "非流动负债合计",
    "total_liability": "负债合计",
    "paidin_capital": "实收资本(股本)",
    "capital_reserve_fund": "资本公积金",
    "treasury_stock": "库存股",
    "surplus_reserve_fund": "盈余公积金",
    "retained_profit": "未分配利润",
    "equities_parent_company_owners": "归属母公司股东权益",
    "minority_interests": "少数股东权益",
    "total_owner_equities": "股东权益合计",
    "total_sheet_owner_equities": "负债和股东权益合计",
}

INCOME_FIELD_ZH = {
    "total_operating_revenue": "营业总收入",
    "operating_revenue": "营业收入",
    "interest_income": "利息收入",
    "total_operating_cost": "营业总成本",
    "operating_cost": "营业成本",
    "interest_expense": "利息支出",
    "operating_tax_surcharges": "营业税金及附加",
    "sale_expense": "销售费用",
    "administration_expense": "管理费用",
    "financial_expense": "财务费用",
    "asset_impairment_loss": "资产减值损失",
    "fair_value_variable_income": "公允价值变动收益",
    "investment_income": "投资收益",
    "invest_income_associates": "对联营/合营企业投资收益",
    "operating_profit": "营业利润",
    "non_operating_revenue": "营业外收入",
    "non_operating_expense": "营业外支出",
    "total_profit": "利润总额",
    "income_tax_expense": "所得税费用",
    "net_profit": "净利润",
    "np_parent_company_owners": "归属母公司净利润",
    "minority_profit": "少数股东损益",
    "basic_eps": "基本每股收益",
    "diluted_eps": "稀释每股收益",
    "other_composite_income": "其他综合收益",
    "total_composite_income": "综合收益总额",
    "ci_parent_company_owners": "归属母公司综合收益",
    "ci_minority_owners": "归属少数股东综合收益",
    "adjusted_profit": "扣非净利润",
}

CASHFLOW_FIELD_ZH = {
    "goods_sale_and_service_render_cash": "销售商品提供劳务收到的现金",
    "tax_levy_refund": "收到的税费返还",
    "other_cashin_related_operate": "收到其他与经营活动有关的现金",
    "subtotal_operate_cash_inflow": "经营活动现金流入小计",
    "goods_and_services_cash_paid": "购买商品接受劳务支付的现金",
    "staff_behalf_paid": "支付给职工的现金",
    "tax_payments": "支付的各项税费",
    "other_operate_cash_paid": "支付其他与经营活动有关的现金",
    "subtotal_operate_cash_outflow": "经营活动现金流出小计",
    "net_operate_cash_flow": "经营活动产生的现金流量净额",
    "invest_withdrawal_cash": "收回投资收到的现金",
    "invest_proceeds": "取得投资收益收到的现金",
    "fix_intan_other_asset_dispo_cash": "处置固定资产等收回的现金净额",
    "other_cash_from_invest_act": "收到其他与投资活动有关的现金",
    "subtotal_invest_cash_inflow": "投资活动现金流入小计",
    "fix_intan_other_asset_acqui_cash": "购建固定资产等支付的现金",
    "invest_cash_paid": "投资支付的现金",
    "other_cash_to_invest_act": "支付其他与投资活动有关的现金",
    "subtotal_invest_cash_outflow": "投资活动现金流出小计",
    "net_invest_cash_flow": "投资活动产生的现金流量净额",
    "cash_from_invest": "吸收投资收到的现金",
    "cash_from_borrowing": "取得借款收到的现金",
    "other_finance_act_cash": "收到其他与筹资活动有关的现金",
    "subtotal_finance_cash_inflow": "筹资活动现金流入小计",
    "borrowing_repayment": "偿还债务支付的现金",
    "dividend_interest_payment": "分配股利/偿付利息支付的现金",
    "other_finance_act_payment": "支付其他与筹资活动有关的现金",
    "subtotal_finance_cash_outflow": "筹资活动现金流出小计",
    "net_finance_cash_flow": "筹资活动产生的现金流量净额",
    "exchange_rate_change_effect": "汇率变动对现金的影响",
    "cash_equivalent_increase": "现金及现金等价物净增加额",
    "cash_equivalents_at_beginning": "期初现金及现金等价物余额",
    "cash_and_equivalents_at_end": "期末现金及现金等价物余额",
}

FINANCE_INDICATOR_FIELD_ZH = {
    "eps": "每股收益EPS",
    "roe": "净资产收益率ROE",
    "inc_return": "扣非ROE",
    "roa": "总资产净利率ROA",
    "net_profit_margin": "销售净利率",
    "gross_profit_margin": "销售毛利率",
    "expense_to_total_revenue": "营业总成本/营业总收入",
    "operation_profit_to_total_revenue": "营业利润/营业总收入",
    "net_profit_to_total_revenue": "净利润/营业总收入",
    "operating_expense_to_total_revenue": "营业费用率",
    "ga_expense_to_total_revenue": "管理费用率",
    "financing_expense_to_total_revenue": "财务费用率",
    "ocf_to_revenue": "经营现金流/营业收入",
    "ocf_to_operating_profit": "经营现金流/经营净收益",
    "inc_total_revenue_year_on_year": "营业总收入同比增长率",
    "inc_revenue_year_on_year": "营业收入同比增长率",
    "inc_operation_profit_year_on_year": "营业利润同比增长率",
    "inc_net_profit_year_on_year": "净利润同比增长率",
    "inc_net_profit_to_shareholders_year_on_year": "归母净利润同比增长率",
    "inc_total_revenue_annual": "营业总收入环比增长率",
    "inc_revenue_annual": "营业收入环比增长率",
    "inc_net_profit_annual": "净利润环比增长率",
}


# ==================== 格式化工具 ====================

def _format_statement_df(
    df: pd.DataFrame,
    title: str,
    field_zh: dict,
    curr_date: Optional[str] = None,
) -> str:
    """将财务报表 DataFrame 格式化为 LLM 可读的文本

    转置为：行=科目(中文)，列=报告期
    """
    if df.empty:
        return f"# {title}\n无数据"

    df = df.copy()

    if curr_date and "datetime" in df.columns:
        df = df[df["datetime"] <= curr_date]

    if df.empty:
        return f"# {title}\n无数据（已按日期 {curr_date} 过滤）"

    period_col = "report_period" if "report_period" in df.columns else None
    if period_col:
        period_labels = df[period_col].tolist()
    else:
        period_labels = [f"第{i+1}期" for i in range(len(df))]

    drop_cols = ["code", "datetime", "report_period", "statement_type"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    df = df[numeric_cols]

    df_t = df.T
    df_t.columns = [str(p) for p in period_labels]

    df_t.index = [field_zh.get(name, name) for name in df_t.index]

    header = f"# {title}\n"
    header += f"# 数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    csv = df_t.to_csv()
    return header + csv


# ==================== 4 个数据获取函数 ====================

def get_fundamentals_overview(symbol: str, curr_date: str) -> str:
    """获取公司基本面概览：公司信息 + 估值指标 + 盈利/成长能力 + 近期分红

    数据来源：TransMatrix 内部数据库
              stock_code / sw_industry / capital / finance_indicator / dividend_allocation
    """
    try:
        from tradingagents.dataflows.providers.china.internal_queries import (
            get_stock_info,
            get_sw_industry,
            get_valuation,
            get_finance_indicator,
            get_dividend,
        )
    except ImportError:
        return f"内部数据库不可用，无法获取 {symbol} 基本面概览数据"

    lines = []
    lines.append(f"# {symbol} 公司基本面概览")
    lines.append(f"# 数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    info = get_stock_info(symbol) or {}
    if info:
        lines.append("## 公司信息")
        lines.append(f"股票名称: {info.get('name', 'N/A')}")
        lines.append(f"所属行业: {info.get('industry', 'N/A')}")
        lines.append(f"所属板块: {info.get('sector', 'N/A')}")
        lines.append(f"所属地区: {info.get('area', 'N/A')}")
        lines.append(f"上市日期: {info.get('list_date', 'N/A')}")

    sw = get_sw_industry(symbol)
    if sw:
        lines.append(
            f"申万行业: {sw.get('sw_l1_name', '')}"
            f" - {sw.get('sw_l2_name', '')}"
            f" - {sw.get('sw_l3_name', '')}"
        )
    lines.append("")

    val = get_valuation(symbol, curr_date) or {}
    if val:
        lines.append("## 估值指标（日频）")
        lines.append(f"总市值: {val.get('market_cap', 'N/A')} 亿元")
        lines.append(f"流通市值: {val.get('circulating_market_cap', 'N/A')} 亿元")
        lines.append(f"市盈率PE(TTM): {val.get('pe_ratio', 'N/A')}")
        lines.append(f"市盈率PE(LYR): {val.get('pe_ratio_lyr', 'N/A')}")
        lines.append(f"市净率PB: {val.get('pb_ratio', 'N/A')}")
        lines.append(f"市销率PS(TTM): {val.get('ps_ratio', 'N/A')}")
        lines.append(f"市现率PCF(TTM): {val.get('pcf_ratio', 'N/A')}")
        lines.append(f"换手率: {val.get('turnover_ratio', 'N/A')}%")
        lines.append(f"总股本: {val.get('capitalization', 'N/A')} 万股")
        lines.append(f"流通股本: {val.get('circulating_cap', 'N/A')} 万股")
    lines.append("")

    fi_df = get_finance_indicator(symbol, limit=4)
    if not fi_df.empty:
        if curr_date and "datetime" in fi_df.columns:
            fi_df = fi_df[fi_df["datetime"] <= curr_date]

        if not fi_df.empty:
            lines.append("## 关键财务指标（近4期）")
            period_col = "report_period" if "report_period" in fi_df.columns else None
            if period_col:
                period_labels = fi_df[period_col].tolist()
                drop_cols = ["code", "datetime", "report_period", "statement_type"]
                fi_clean = fi_df.drop(
                    columns=[c for c in drop_cols if c in fi_df.columns],
                    errors="ignore",
                )
                numeric_cols = fi_clean.select_dtypes(include="number").columns.tolist()
                fi_clean = fi_clean[numeric_cols]

                fi_t = fi_clean.T
                fi_t.columns = [str(p) for p in period_labels]
                fi_t.index = [
                    FINANCE_INDICATOR_FIELD_ZH.get(n, n) for n in fi_t.index
                ]
                lines.append(fi_t.to_csv())
            else:
                lines.append(fi_df.to_csv(index=False))
    lines.append("")

    div_df = get_dividend(symbol, limit=3)
    if not div_df.empty:
        lines.append("## 近期分红")
        for _, row in div_df.iterrows():
            report_date = row.get("report_date", "N/A")
            bonusnote = row.get(
                "implementation_bonusnote",
                row.get("shareholders_plan_bonusnote", "N/A"),
            )
            lines.append(f"  {report_date}: {bonusnote}")
        lines.append("")

    return "\n".join(lines)


def get_balance_sheet_data(
    symbol: str,
    freq: str = "quarterly",
    curr_date: Optional[str] = None,
) -> str:
    """获取资产负债表原始数据

    数据来源：TransMatrix 内部数据库 balance 表
    返回格式：行=科目(中文名)，列=报告期，值=金额(元)
    """
    try:
        from tradingagents.dataflows.providers.china.internal_queries import (
            get_balance,
        )
    except ImportError:
        return f"内部数据库不可用，无法获取 {symbol} 资产负债表"

    limit = 4 if freq == "quarterly" else 3
    df = get_balance(symbol, limit=limit)

    title = f"{symbol} 资产负债表 ({freq})"
    return _format_statement_df(df, title, BALANCE_FIELD_ZH, curr_date)


def get_cashflow_data(
    symbol: str,
    freq: str = "quarterly",
    curr_date: Optional[str] = None,
) -> str:
    """获取现金流量表原始数据

    数据来源：TransMatrix 内部数据库 cashflow 表
    返回格式：行=科目(中文名)，列=报告期，值=金额(元)
    """
    try:
        from tradingagents.dataflows.providers.china.internal_queries import (
            get_cashflow,
        )
    except ImportError:
        return f"内部数据库不可用，无法获取 {symbol} 现金流量表"

    limit = 4 if freq == "quarterly" else 3
    df = get_cashflow(symbol, limit=limit)

    title = f"{symbol} 现金流量表 ({freq})"
    return _format_statement_df(df, title, CASHFLOW_FIELD_ZH, curr_date)


def get_income_statement_data(
    symbol: str,
    freq: str = "quarterly",
    curr_date: Optional[str] = None,
) -> str:
    """获取利润表原始数据

    数据来源：TransMatrix 内部数据库 income 表
    返回格式：行=科目(中文名)，列=报告期，值=金额(元)
    """
    try:
        from tradingagents.dataflows.providers.china.internal_queries import (
            get_income,
        )
    except ImportError:
        return f"内部数据库不可用，无法获取 {symbol} 利润表"

    limit = 4 if freq == "quarterly" else 3
    df = get_income(symbol, limit=limit)

    title = f"{symbol} 利润表 ({freq})"
    return _format_statement_df(df, title, INCOME_FIELD_ZH, curr_date)
