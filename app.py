import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Set page config
st.set_page_config(
    page_title="UK Salary Take-Home Calculator",
    page_icon="",
    layout="wide"
)

def calculate_take_home(gross_salary, pension_percent=0):
    """Calculate UK take-home salary, including taxes and pension"""
    pension_contribution = (gross_salary * pension_percent) / 100
    salary_after_pension = gross_salary - pension_contribution
    
    # Personal allowance (reduces by £1 for every £2 over £100,000)
    personal_allowance = 12570
    if gross_salary > 100000:
        personal_allowance = max(0, personal_allowance - ((gross_salary - 100000) / 2))
    
    taxable_income = max(0, salary_after_pension - personal_allowance)
    
    # Income tax calculation
    income_tax = 0
    if taxable_income > 125140:  # Additional rate
        income_tax += (taxable_income - 125140) * 0.45
        income_tax += (125140 - 37700) * 0.40
        income_tax += 37700 * 0.20
    elif taxable_income > 37700:  # Higher rate
        income_tax += (taxable_income - 37700) * 0.40
        income_tax += 37700 * 0.20
    elif taxable_income > 0:  # Basic rate
        income_tax += taxable_income * 0.20
    
    # National Insurance: on gross salary minus pension
    national_insurance = 0
    ni_threshold = 12570  # Primary threshold
    upper_threshold = 50270
    
    if salary_after_pension > upper_threshold:
        national_insurance += (salary_after_pension - upper_threshold) * 0.02
        national_insurance += (upper_threshold - ni_threshold) * 0.12
    elif salary_after_pension > ni_threshold:
        national_insurance += (salary_after_pension - ni_threshold) * 0.12
    
    take_home = salary_after_pension - income_tax - national_insurance
    effective_rate = ((gross_salary - take_home) / gross_salary) * 100
    
    return {
        'gross': gross_salary,
        'pension_contribution': pension_contribution,
        'salary_after_pension': salary_after_pension,
        'income_tax': income_tax,
        'national_insurance': national_insurance,
        'take_home': take_home,
        'effective_rate': effective_rate
    }

def format_currency(value):
    """Format value as UK currency"""
    return f"£{value:,.0f}"

def create_salary_data(max_salary, pension_rate):
    """Generate salary data for charts"""
    salaries = np.linspace(15000, max_salary, 50)
    data = []
    
    for salary in salaries:
        result = calculate_take_home(salary, pension_rate)
        data.append({
            'salary': salary,
            'gross': salary,
            'take_home': result['take_home'],
            'difference': salary - result['take_home'],
            'effective_rate': result['effective_rate'],
            'income_tax': result['income_tax'],
            'national_insurance': result['national_insurance'],
            'pension': result['pension_contribution']
        })
    
    return pd.DataFrame(data)

def display_salary_card(title, data, color):
    """Display salary breakdown card"""
    with st.container():
        st.markdown(f"""
        <div style="border: 2px solid {color}; border-radius: 10px; padding: 20px; margin: 10px 0; background-color: rgba(52, 152, 219, 0.1);">
        <h3>{title}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Gross Salary:**")
            st.write("**Income Tax:**")
            st.write("**National Insurance:**")
            if data['pension_contribution'] > 0:
                st.write("**Pension Contribution:**")
            st.write("**Take Home:**")
            st.write("**Monthly:**")
            st.write("**Effective Tax Rate:**")
        
        with col2:
            st.write(format_currency(data['gross']))
            st.write(f"-{format_currency(data['income_tax'])}")
            st.write(f"-{format_currency(data['national_insurance'])}")
            if data['pension_contribution'] > 0:
                st.write(f"-{format_currency(data['pension_contribution'])}")
            st.write(f"**{format_currency(data['take_home'])}**")
            st.write(format_currency(data['take_home'] / 12))
            st.write(f"{data['effective_rate']:.1f}%")

# Main app
def main():
    st.title("🇬🇧 UK PAYE CALC 2025/6")
    st.markdown("Compare take-home salaries after Income Tax, National Insurance, and pension contributions.")
    
    # Sidebar controls
    st.sidebar.header("Compare Salaries")
    salary1 = st.sidebar.number_input("Salary 1 (£)", 15000, 200000, 35000, 1000)
    salary2 = st.sidebar.number_input("Salary 2 (£)", 15000, 200000, 50000, 1000)

    st.sidebar.header("Settings")
    pension_rate = st.sidebar.slider("Pension Contribution %", 0.0, 15.0, 3.0, 0.5)
    max_salary = st.sidebar.slider("Maximum Salary for Chart", 50000, 200000, 100000, 10000)
    
    # Calculate comparisons
    salary1_analysis = calculate_take_home(salary1, pension_rate)
    salary2_analysis = calculate_take_home(salary2, pension_rate)
    
    # Salary comparison cards
    st.header("Salary Comparison")
    col1, col2 = st.columns(2)
    
    with col1:
        display_salary_card(f"Salary {format_currency(salary1)}", salary1_analysis, "#3498db")
    
    with col2:
        display_salary_card(f"Salary {format_currency(salary2)}", salary2_analysis, "#2ecc71")
    
    # Difference analysis
    st.header("Difference Analysis")
    col1, col2, col3 = st.columns(3)
    
    gross_diff = salary2 - salary1
    takehome_diff = salary2_analysis['take_home'] - salary1_analysis['take_home']
    keep_percentage = (takehome_diff / gross_diff) * 100 if gross_diff != 0 else 0
    
    with col1:
        st.metric("Gross Difference", format_currency(gross_diff))
    
    with col2:
        st.metric("Net Difference", format_currency(takehome_diff))
    
    with col3:
        st.metric("What Would You Keep?", f"{keep_percentage:.1f}%")
    
    # Generate chart data
    df = create_salary_data(max_salary, pension_rate)
    
    # Gross vs Take-Home Chart
    st.header("Total vs Take-Home Salary")
    fig1 = go.Figure()
    
    fig1.add_trace(go.Scatter(
        x=df['salary'],
        y=df['gross'],
        mode='lines',
        name='Total Salary',
        line=dict(color='blue', dash='dash', width=2)
    ))
    
    fig1.add_trace(go.Scatter(
        x=df['salary'],
        y=df['take_home'],
        mode='lines',
        name='Take-Home Salary',
        line=dict(color='green', width=3)
    ))
    
    fig1.update_layout(
        xaxis_title="Gross Salary (£)",
        yaxis_title="Amount (£)",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Effective Tax Rate Chart
    st.header("Effective Tax Rate by Salary")
    fig2 = px.line(df, x='salary', y='effective_rate',
                   title='Effective Tax Rate (%)',
                   labels={'salary': 'Gross Salary (£)', 'effective_rate': 'Effective Tax Rate (%)'})
    fig2.update_traces(line_color='orange', line_width=3)
    fig2.update_layout(height=400)
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # Tax Breakdown Chart
    st.header("Tax Breakdown by Component")
    
    # Sample every 5th row for cleaner visualization
    df_sampled = df.iloc[::5].copy()
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        x=df_sampled['salary'],
        y=df_sampled['income_tax'],
        name='Income Tax',
        marker_color='red'
    ))
    
    fig3.add_trace(go.Bar(
        x=df_sampled['salary'],
        y=df_sampled['national_insurance'],
        name='National Insurance',
        marker_color='orange'
    ))
    
    if pension_rate > 0:
        fig3.add_trace(go.Bar(
            x=df_sampled['salary'],
            y=df_sampled['pension'],
            name='Pension Contribution',
            marker_color='blue'
        ))
    
    fig3.update_layout(
        barmode='stack',
        xaxis_title="Gross Salary (£)",
        yaxis_title="Amount (£)",
        height=500
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    # Data table
    if st.checkbox("Show detailed breakdown table"):
        st.header("Detailed Breakdown")
        display_df = df.copy()
        for col in ['gross', 'take_home', 'income_tax', 'national_insurance', 'pension']:
            display_df[col] = display_df[col].apply(lambda x: f"£{x:,.0f}")
        display_df['effective_rate'] = display_df['effective_rate'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            display_df[['salary', 'gross', 'take_home', 'income_tax', 'national_insurance', 'pension', 'effective_rate']],
            use_container_width=True
        )
    
    # Footer
    st.markdown("---")
    st.caption("Tax rules used in this model — click to expand for details")

    with st.expander("Tax calculation details"):
        st.markdown("""
        - Personal allowance: £12,570 (reduced by £1 for every £2 of income over £100,000).
        - Income tax on taxable income (2024/25 model):
          - 20% basic rate up to £37,700
          - 40% higher rate from £37,700 to £125,140
          - 45% additional rate above £125,140
        - National Insurance (Class 1 employee, modelled):
          - 12% on earnings between £12,570 and £50,270
          - 2% on earnings above £50,270
        - Pension contributions in this model are deducted from gross pay before tax and NI.
        - Exclusions: student loans, salary sacrifice schemes, employer pension contributions, PAYE code adjustments and other deductions are not modelled.
        - Based on UK 2024/25 rates. Official references:
          - https://www.gov.uk/income-tax-rates
          - https://www.gov.uk/national-insurance-rates
        """)

if __name__ == "__main__":
    main()