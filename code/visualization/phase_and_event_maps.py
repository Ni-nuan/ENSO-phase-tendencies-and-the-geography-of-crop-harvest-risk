"""Render the stored figure-level results without fitting models."""
from pathlib import Path
import sys
import numpy as np,pandas as pd,geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import fitz
R=Path(__file__).resolve().parents[2]
O=R/'build/phase_and_event_maps'
for folder in ['figures','qa']: (O/folder).mkdir(parents=True,exist_ok=True)
S=R/'source_data/main_figures/phase_and_event_maps';read=lambda k:pd.read_csv(S/(k+'.csv'))
C=['MAIZE','RICE','SOY','WHEAT'];names=['Maize','Rice','Soybean','Wheat'];factors=['P','T','VPD','SM','SW']
factor_names=['Precipitation','Temperature','Air dryness','Soil moisture','Radiation']
cropcolors=['#0072B2','#009E73','#CC79A7','#D55E00'];markers=['o','s','^','D'];envcolors=['#0072B2','#D55E00']
models={'Observed yield':('#0072B2','o'),'Historical model fit':('#009E73','s'),'Five-weather contribution':('#CC79A7','^')}
plt.rcParams.update({'font.family':'Arial','font.size':7,'axes.titlesize':7.8,'axes.labelsize':7,'xtick.labelsize':6,'ytick.labelsize':6,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
world=gpd.read_file('zip://'+str(R/'source_data/basemap/ne_50m_admin_0_countries.zip'));world=world[world.ADM0_A3.ne('ATA')]
def title(ax,label,text):ax.set_title(label+'  '+text,loc='left',fontweight='bold',pad=6)
def grid(rows=2,height=6.3):
    fig,axs=plt.subplots(rows,2,figsize=(180/25.4,height));fig.subplots_adjust(left=.115,right=.98,bottom=.10,top=.95,wspace=.34,hspace=.56);return fig,axs
def save(fig,axes,n,letters=None):
    axes=list(np.asarray(axes,dtype=object).flat);fig.canvas.draw()
    groups=dict(row_groups=[['a','b'],['d','e'],['g','h'],['j','k']],column_groups=[['a','d','g','j'],['b','e','h','k'],['c','f','i','l']]) if n==1 else {}

    fig.savefig(O/f'figures/Figure_{n}.png',dpi=300)
    fig.savefig(O/f'figures/Figure_{n}.pdf')
    fig.savefig(O/f'figures/Figure_{n}.svg')
    Image.open(O/f'figures/Figure_{n}.png').convert('L').save(O/f'qa/Figure_{n}_grayscale.png')
    with fitz.open(O/f'figures/Figure_{n}.pdf') as doc:doc[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(str(O/f'qa/Figure_{n}_PDF_preview.png'))
    plt.close(fig)
def boxes(ax,arrays,labels,colors,horizontal=False,show_points=False):
    for i,(values,color) in enumerate(zip(arrays,colors)):
        values=np.asarray(values,dtype=float);values=values[np.isfinite(values)]
        ax.boxplot([values],positions=[i],orientation='horizontal' if horizontal else 'vertical',widths=.42,whis=(0,100),showfliers=False,showmeans=True,patch_artist=True,
            boxprops=dict(facecolor=color,alpha=.16,edgecolor=color),medianprops=dict(color=color,linewidth=1.5),whiskerprops=dict(color=color,linewidth=.8),capprops=dict(color=color,linewidth=.8),meanprops=dict(marker='D',markersize=4,markerfacecolor=color,markeredgecolor='white',markeredgewidth=.4))
        if show_points:
            jitter=np.linspace(-.12,.12,len(values))
            ax.scatter(i+jitter,values,s=8,color=color,alpha=.55,zorder=3)
    if horizontal:ax.set(yticks=range(len(labels)),yticklabels=labels)
    else:ax.set(xticks=range(len(labels)),xticklabels=labels)

# Fig1: four crop blocks, each with two wide maps above a full-width event strip.
fig=plt.figure(figsize=(180/25.4,240/25.4));outer=fig.add_gridspec(4,1,left=.065,right=.98,bottom=.08,top=.965,hspace=.20)
axes=[];phase=read('phase_annual');maprows=[];signrows=[];event_order=read('Figure1_EVENT_AXIS');events=event_order.physical_event_id.tolist()
for i,crop in enumerate(C):
    gs=outer[i].subgridspec(2,2,height_ratios=[3,1.4],hspace=.18,wspace=.08)
    for j,p in enumerate(['EN','LN']):
        ax=fig.add_subplot(gs[0,j]);axes.append(ax)
        d=phase[(phase.crop==crop)&phase.phase.eq(p)&phase.main_eligible].copy();d['iso3']=d.system_id.str.split('×').str[0];maprows.append(d)
        z=world.merge(d[['iso3','delta_mean']],left_on='ADM0_A3',right_on='iso3',how='left')
        z.plot(ax=ax,column='delta_mean',cmap='RdBu',vmin=-20,vmax=20,missing_kwds={'color':'#e4e4e4'},edgecolor='#b8b8b8',linewidth=.15,aspect=None)
        for sign,marker in [(1,'^'),(-1,'v')]:
            subset=z[z.delta_mean*sign>0];pts=subset.geometry.representative_point();ax.scatter(pts.x,pts.y,marker=marker,s=2.2,color='.25',alpha=.8,linewidths=0,zorder=3)
            signrows.extend(dict(system_id=row.iso3+'×'+crop,phase=p,delta_mean=row.delta_mean,marker=marker,x=float(pt.x),y=float(pt.y)) for row,pt in zip(subset.itertuples(),pts))
        ax.set(xlim=(-180,180),ylim=(-58,85));ax.set_aspect('auto');ax.set_axis_off()
        title(ax,'abcdefghijkl'[i*3+j],names[i]+' · '+('El Niño' if p=='EN' else 'La Niña'))
    ax=fig.add_subplot(gs[1,:]);axes.append(ax);g=read('Figure1_event_matrix_'+crop)
    producers=g[['iso3','Q_2012_2020','calendar_withheld_display']].drop_duplicates('iso3').sort_values('Q_2012_2020',ascending=False).head(5)
    matrix=np.full((len(producers),len(events)),np.nan)
    for k,r in enumerate(producers.itertuples()):
        q=g[(g.iso3==r.iso3)&g.is_primary_eligible&~g.calendar_withheld_display]
        for row in q.itertuples():matrix[k,events.index(row.physical_event_id)]=row.primary_signed_mean
    ax.set_facecolor('#e4e4e4');ax.imshow(matrix,aspect='auto',cmap='RdBu',vmin=-30,vmax=30,interpolation='none')
    yy,xx=np.where(matrix<0);ax.scatter(xx,yy,s=1.5,c='black',linewidths=0)
    ax.set_yticks(range(len(producers)),[r.iso3+(' ×' if r.calendar_withheld_display else '') for r in producers.itertuples()])
    ax.set_xticks(range(len(events)),[x[3:7][2:]+('E' if x.startswith('EN') else 'L') for x in events]);ax.tick_params(axis='x',labelsize=5.8,pad=2,length=2)
    ax.tick_params(axis='y',pad=1,labelsize=5.7,length=2)
    ax.set_title('cfil'[i]+'  Event yields in major producers',loc='left',fontweight='bold',fontsize=7.3,pad=2)
pd.DataFrame(signrows).to_csv(O/'figures/FIGURE1_SIGN_MARKS.csv',index=False)
ca=fig.add_axes([.075,.038,.41,.008]);fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(-20,20),cmap='RdBu'),cax=ca,orientation='horizontal');ca.tick_params(labelsize=5.8);ca.set_xlabel('Mean yield difference from neutral years (pp)',fontsize=6.2)
ca=fig.add_axes([.59,.038,.35,.008]);fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(-30,30),cmap='RdBu'),cax=ca,orientation='horizontal');ca.tick_params(labelsize=5.8);ca.set_xlabel('Actual event yield anomaly (%)',fontsize=6.2)
fig.legend(handles=[plt.Line2D([],[],marker='^',ls='',ms=2.8,color='.25',label='Higher than neutral'),plt.Line2D([],[],marker='v',ls='',ms=2.8,color='.25',label='Lower than neutral'),plt.Line2D([],[],marker='x',ls='',ms=3,color='.25',label='Calendar withheld')],loc='center',bbox_to_anchor=(.52,.055),ncol=3,frameon=False,fontsize=5.6)
save(fig,axes,1)

