"""
Temporal trajectory analysis for Phase 2 (activity count only — fast).

For each subreddit, computes mean monthly activity (posts + comments) for:
  - Pre-churn users:  aligned to 'months before last calibration-period activity'
  - Active users:     aligned to 'months before holdout start (July 1 2025)'

Only users with recency_cal >= 12 weeks (3+ months of history) are included
in the churned group so that a meaningful 6-month window exists.

Saves: ../w7_hm/figure7_trajectory.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PROCESSED_DIR     = '../data/processed_data/'
HOLDOUT_START     = pd.Timestamp('2025-07-01', tz='UTC')
N_MONTHS          = 6
RECENCY_MIN_WEEKS = 12    # 3 months minimum
SEED              = 42


def compute_trajectory(sub):
    print(f"  {sub}: loading churn labels...", flush=True)
    churn = pd.read_parquet(
        f'{PROCESSED_DIR}churn_{sub}.parquet',
        columns=['author', 'last_cal', 'churned', 'recency_cal']
    )
    churn['last_cal'] = pd.to_datetime(churn['last_cal'], utc=True)

    churned_elig = churn[(churn['churned'] == 1) & (churn['recency_cal'] >= RECENCY_MIN_WEEKS)]
    active_all   = churn[churn['churned'] == 0].copy()
    active_all['ref_date'] = HOLDOUT_START
    n_ch, n_ac = len(churned_elig), len(active_all)
    print(f"  {sub}: eligible churned={n_ch:,}  active={n_ac:,}", flush=True)

    # Build reference-date table for all users
    ref_churned = churned_elig[['author', 'last_cal', 'churned']].copy()
    ref_churned.rename(columns={'last_cal': 'ref_date'}, inplace=True)
    ref_all = pd.concat([ref_churned, active_all[['author', 'ref_date', 'churned']]])

    all_users = set(ref_all['author'])

    # Load activity (just timestamps — very fast)
    print(f"  {sub}: loading activity...", flush=True)
    act = pd.read_parquet(f'{PROCESSED_DIR}activity_{sub}.parquet')
    act = act[(act['created_utc'] < HOLDOUT_START) & act['author'].isin(all_users)].copy()
    act['month'] = act['created_utc'].dt.to_period('M')

    # Monthly count per user
    monthly = act.groupby(['author', 'month']).size().reset_index(name='n_posts')

    # Attach reference month
    monthly = monthly.merge(ref_all, on='author')
    monthly['ref_month'] = monthly['ref_date'].dt.to_period('M')
    monthly['months_rel'] = monthly.apply(
        lambda r: (r['ref_month'] - r['month']).n, axis=1
    )

    # Keep last N_MONTHS, flip sign
    traj = monthly[(monthly['months_rel'] >= 0) & (monthly['months_rel'] < N_MONTHS)].copy()
    traj['months_rel'] = -traj['months_rel']    # -5 = 5 months before last activity

    result = traj.groupby(['months_rel', 'churned']).agg(
        mean_activity=('n_posts', 'mean'),
        n_users=('author', 'nunique')
    ).reset_index()

    print(f"  {sub}: done.", flush=True)
    return result


# ── Run ─────────────────────────────────────────────────────────────────────
print("=== Computing activity trajectories ===")
traj_lp     = compute_trajectory('lp')
traj_loseit = compute_trajectory('loseit')
traj_dep    = compute_trajectory('dep')

# ── Plot ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)

subreddits = ['r/learnprogramming', 'r/loseit', 'r/depression']
trajs      = [traj_lp, traj_loseit, traj_dep]
colors     = {0: '#1f77b4', 1: '#d62728'}
labels_map = {0: 'Active', 1: 'Pre-churn'}

for col, (sub, traj) in enumerate(zip(subreddits, trajs)):
    ax = axes[col]
    for c in [0, 1]:
        s = traj[traj['churned'] == c].sort_values('months_rel')
        if len(s):
            ax.plot(s['months_rel'], s['mean_activity'],
                    marker='o', label=labels_map[c],
                    color=colors[c], linewidth=2.2, markersize=6)
    ax.set_title(sub, fontsize=12, fontweight='bold')
    ax.set_xlabel('Months before last activity', fontsize=10)
    ax.set_xticks(range(-N_MONTHS + 1, 1))
    if col == 0:
        ax.set_ylabel('Mean monthly posts + comments', fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)

plt.tight_layout()
out_path = '../w7_hm/figure7_trajectory.png'
plt.savefig(out_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved {out_path}")

# ── Print key numbers for README ────────────────────────────────────────────
print("\n=== Key numbers ===")
for sub_name, traj in zip(subreddits, trajs):
    print(f"\n{sub_name}")
    for c in [0, 1]:
        s = traj[traj['churned']==c].sort_values('months_rel')
        if len(s) >= 2:
            first = s.iloc[0]['mean_activity']
            last  = s.iloc[-1]['mean_activity']
            label = labels_map[c]
            pct   = (last - first) / first * 100 if first != 0 else float('nan')
            print(f"  {label}: month {s.iloc[0]['months_rel']:.0f} = {first:.2f}, "
                  f"month {s.iloc[-1]['months_rel']:.0f} = {last:.2f}  ({pct:+.1f}%)")
