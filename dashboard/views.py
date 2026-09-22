from decimal import Decimal

import plotly.graph_objects as go
from plotly.offline import plot
from django.shortcuts import render, get_object_or_404

from core.models import Project
from budgeting.models import Budget
from budgeting.services import variance_by_subtype, impairment_risk_assessment
from revenue.models import RevenueContract
from investors.models import Investor, Investment, Distribution
from investors.services import investor_roi

PLOTLY_CONFIG = {'displayModeBar': False, 'responsive': True}


def _plot_div(fig, **layout_kwargs):
    fig.update_layout(
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Helvetica, Arial, sans-serif', size=13, color='#2b2b2b'),
        **layout_kwargs,
    )
    return plot(fig, output_type='div', include_plotlyjs=False, config=PLOTLY_CONFIG)


def project_list(request):
    projects = Project.objects.all().order_by('title')
    return render(request, 'dashboard/project_list.html', {'projects': projects})


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    budget = Budget.objects.filter(project=project).order_by('-version').first()

    context = {'project': project, 'budget': budget}

    if budget:
        rollup = variance_by_subtype(budget)
        subtypes = list(rollup.keys())
        budgeted_vals = [float(rollup[s]['budgeted']) for s in subtypes]
        actual_vals = [float(rollup[s]['actual']) for s in subtypes]

        variance_fig = go.Figure(data=[
            go.Bar(name='Budgeted', x=subtypes, y=budgeted_vals, marker_color='#5b8def'),
            go.Bar(name='Actual', x=subtypes, y=actual_vals, marker_color='#e0623d'),
        ])
        variance_fig.update_layout(barmode='group', title='Budget vs. Actual by Cost Category', yaxis_title='USD')
        context['variance_chart'] = _plot_div(variance_fig)
        context['variance_rows'] = [
            {
                'subtype': s,
                'budgeted': rollup[s]['budgeted'],
                'actual': rollup[s]['actual'],
                'variance': rollup[s]['variance'],
                'variance_pct': rollup[s]['variance_pct'],
            }
            for s in subtypes
        ]

        risk = impairment_risk_assessment(project, budget)
        context['risk'] = risk

    # Revenue recognition: contracted vs recognized, per contract
    contracts = RevenueContract.objects.filter(project=project)
    if contracts.exists():
        names = [c.counterparty for c in contracts]
        contracted = [float(c.total_contract_value) for c in contracts]
        recognized = [float(c.total_recognized) for c in contracts]

        revenue_fig = go.Figure(data=[
            go.Bar(name='Contracted', x=names, y=contracted, marker_color='#b7c4d6'),
            go.Bar(name='Recognized to Date', x=names, y=recognized, marker_color='#2f9e6e'),
        ])
        revenue_fig.update_layout(barmode='overlay', title='Revenue Recognition: Contracted vs. Recognized', yaxis_title='USD')
        context['revenue_chart'] = _plot_div(revenue_fig)
        context['contracts'] = contracts

    # Investor ROI table + distribution breakdown
    investments = Investment.objects.filter(project=project).select_related('investor')
    investor_ids = investments.values_list('investor_id', flat=True).distinct()
    investor_rows = []
    for investor in Investor.objects.filter(id__in=investor_ids):
        contributed = sum((i.amount for i in investments if i.investor_id == investor.id), Decimal('0'))
        roi = investor_roi(project, investor)
        investor_rows.append({'investor': investor, 'contributed': contributed, 'roi': roi})
    context['investor_rows'] = investor_rows

    distributions = Distribution.objects.filter(project=project).prefetch_related('line_items__investor', 'line_items__tier')
    if distributions.exists():
        tier_totals = {}
        for dist in distributions:
            for item in dist.line_items.all():
                key = item.tier.get_tier_type_display()
                tier_totals[key] = tier_totals.get(key, Decimal('0')) + item.amount
        if tier_totals:
            waterfall_fig = go.Figure(data=[go.Pie(
                labels=list(tier_totals.keys()),
                values=[float(v) for v in tier_totals.values()],
                hole=0.45,
                marker_colors=['#5b8def', '#2f9e6e', '#e0a83d'],
            )])
            waterfall_fig.update_layout(title='Distributions by Waterfall Tier')
            context['waterfall_chart'] = _plot_div(waterfall_fig)
    context['distributions'] = distributions

    return render(request, 'dashboard/project_detail.html', context)
