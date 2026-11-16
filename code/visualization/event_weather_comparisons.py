"""Figure 4a alternatives only; no agricultural-model estimation."""
from pathlib import Path
import sys,json,hashlib,shutil
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.lines import Line2D
from PIL import Image
import fitz
R=Path(__file__).resolve().parents[2]
O=R/'build/event_weather_comparisons'
S=R/'source_data/main_figures/event_weather_comparisons'
for folder in ['figures','qa','variants']: (O/folder).mkdir(parents=True,exist_ok=True)
ev=pd.read_csv(S/'event.csv');pairs=pd.read_csv(S/'arg_zaf.csv');usa=pd.read_csv(S/'Figure4_USA_CROSSCROP.csv');cases=pd.read_csv(S/'Figure4_SELECTED_CONTRASTS.csv')
C=['MAIZE','RICE','SOY','WHEAT'];names=['Maize','Rice','Soybean','Wheat'];colors=['#0072B2','#009E73','#CC79A7','#D55E00'];markers=['o','s','^','D'];linestyles=['solid','dashed','dashdot','dotted']
series=[('Y','Observed yield','#0072B2','o'),('prediction_Y','Full historical model','#009E73','s'),('weather_SHAP_pp','Five-weather contribution','#CC79A7','^')]
plt.rcParams.update({'font.family':'Arial','font.size':7,'axes.titlesize':7.8,'axes.labelsize':7,'xtick.labelsize':6,'ytick.labelsize':6,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
summary=[]
for crop in C:
    d=ev[ev.system_id.str.endswith('×'+crop)];xy=d[['Y','weather_SHAP_pp']].to_numpy();z=np.load(S/f'{crop}_DISPLAY_LAYERS.npz');q=np.quantile(xy,[.25,.5,.75],axis=0)
    delta=xy-q[1];dist=np.einsum('ni,ij,nj->n',delta,np.linalg.inv(z['covariance']),delta)
    cut=float(np.quantile(dist,.75));eig,vec=np.linalg.eigh(z['covariance'])
    summary.append(dict(crop=crop,records=len(d),x_q25=q[0,0],x_median=q[1,0],x_q75=q[2,0],y_q25=q[0,1],y_median=q[1,1],y_q75=q[2,1],ellipse_center_x=q[1,0],ellipse_center_y=q[1,1],ellipse_width=2*np.sqrt(eig[1]*cut),ellipse_height=2*np.sqrt(eig[0]*cut),ellipse_angle=float(np.degrees(np.arctan2(vec[1,1],vec[0,1]))),ellipse_distance_cutoff=cut,ellipse_empirical_record_fraction=float((dist<=cut).mean())))
summary=pd.DataFrame(summary).set_index('crop');summary.to_csv(O/'qa/PANEL_A_MEDIAN_IQR_SUMMARY.csv')
def title(ax,letter,first,second):ax.set_title(letter+'  '+first+'\n'+second,loc='left',fontweight='bold',pad=7,linespacing=1.2)
def zero(ax):ax.axhline(0,c='.65',lw=.6,zorder=.2);ax.axvline(0,c='.65',lw=.6,zorder=.2)
def draw_a(ax,kind,label):
    drawn=[];summary_artists=[]
    for crop,color,marker,ls in zip(C,colors,markers,linestyles):
        d=ev[ev.system_id.str.endswith('×'+crop)];z=np.load(S/f'{crop}_DISPLAY_LAYERS.npz');q=summary.loc[crop]
        if kind=='A':
            ax.add_patch(Ellipse((q.ellipse_center_x,q.ellipse_center_y),q.ellipse_width,q.ellipse_height,angle=q.ellipse_angle,facecolor='none',edgecolor=color,linewidth=.55,linestyle=ls,alpha=.5,zorder=.5))
        else:
            X,Y=np.meshgrid(z['xgrid'],z['ygrid']);ax.contour(X,Y,z['density'],levels=[float(z['kde_threshold'])],colors=[color],linewidths=.55,linestyles=ls,alpha=.6,zorder=.5)
        raw=ax.scatter(d.Y,d.weather_SHAP_pp,s=2,alpha=.14,c=color,marker=marker,edgecolors='none',zorder=1)
        drawn.extend(dict(source_csv_row=int(i)+2,crop=crop,x=float(x),y=float(y)) for i,(x,y) in zip(d.index,raw.get_offsets()))
        if kind=='A':
            ax.plot([q.x_q25,q.x_q75],[q.y_median,q.y_median],c=color,lw=.9,zorder=3)
            ax.plot([q.x_median,q.x_median],[q.y_q25,q.y_q75],c=color,lw=.9,zorder=3)
        ax.plot(q.x_median,q.y_median,marker=marker,ms=3,mfc='white',mec=color,mew=.8,ls='',zorder=4)
        summary_artists.append(dict(crop=crop,median=[q.x_median,q.y_median],horizontal_iqr=[q.x_q25,q.x_q75],vertical_iqr=[q.y_q25,q.y_q75]))
    zero(ax);ax.set(xlim=(-70,100),ylim=(-28,23),xlabel='Observed yield anomaly (%)',ylabel=label);ax.xaxis.labelpad=1.5;title(ax,'a','Four crops','1,804 system–event records')
    return drawn,summary_artists

def summary_key(fig):
    # Separate marginal summaries in the former crop-legend space; no event is displaced.
    specs=[(.173,.071,'Yield (%)','x',(-6,7),[-5,0,5]),(.277,.071,'Weather (pp)','y',(-2,3),[-1,0,2])]
    axes=[]
    for left,width,lab,stem,limits,ticks in specs:
        ax=fig.add_axes([left,.5125,width,.058]);axes.append(ax)
        for i,(crop,color,marker) in enumerate(zip(C,colors,markers)):
            r=summary.loc[crop];ax.plot([r[stem+'_q25'],r[stem+'_q75']],[3-i,3-i],c=color,lw=.95);ax.plot(r[stem+'_median'],3-i,marker=marker,ms=2.4,mfc='white',mec=color,mew=.65,ls='')
        ax.set(xlim=limits,ylim=(-.6,3.6),yticks=[],xticks=ticks);ax.tick_params(axis='x',labelsize=5.2,pad=1,length=0,width=.5)
        ax.spines['left'].set_visible(False);ax.spines['bottom'].set_linewidth(.5);ax.axvline(0,c='.8',lw=.4,zorder=0)
        ax.set_title(lab,fontsize=5.7,fontweight='normal',pad=1)
    for i,(name,color,marker) in enumerate(zip(names,colors,markers)):
        y=.5125+.058*((3-i+.6)/4.2)
        fig.text(.108,y,name,fontsize=5.2,color=color,va='center')
    return axes

def render(kind,label_id='modelled'):
    label='Modelled yield contribution from\nfive weather factors (pp)' if label_id=='modelled' else 'Yield anomaly contribution from\nfive weather factors (pp)'
    tag=kind if label_id=='modelled' else kind+'_label2'
    fig,axs=plt.subplots(2,3,figsize=(180/25.4,150/25.4));fig.subplots_adjust(left=.105,right=.985,bottom=.19,top=.89,wspace=.50,hspace=.76)
    drawn,summaries=draw_a(axs[0,0],kind,label);case_artists=[]
    if kind=='A':summary_key(fig)
    else:axs[0,0].legend(handles=[Line2D([],[],ls=ls,marker=m,color=c,ms=3,lw=.55,label=n) for n,c,m,ls in zip(names,colors,markers,linestyles)],fontsize=5.7,frameon=False,ncol=2,loc='upper left',bbox_to_anchor=(0,-.35),columnspacing=.8,handletextpad=.4)
    ax=axs[0,1];b=ax.scatter(pairs.Y_a,pairs.Y_b,s=14,color='#0072B2',alpha=.85,zorder=2);ax.plot([-65,50],[-65,50],ls='--',c='.6',lw=.6,zorder=.2);zero(ax)
    ax.set(xlim=(-65,50),ylim=(-65,50),xlabel='Argentine maize\nyield anomaly (%)',ylabel='South African maize\nyield anomaly (%)');title(ax,'b','Argentina–South Africa','8 shared El Niño events')
    r=pairs[pairs.matched_years_a.astype(str).eq('1993')].iloc[0];ax.annotate('1993',(r.Y_a,r.Y_b),xytext=(4,3),textcoords='offset points',fontsize=5.8)
    bcoords=np.asarray(b.get_offsets()).tolist()
    ax=axs[0,2];c=ax.scatter(usa['USA×MAIZE'],usa['USA×SOY'],s=14,color='#0072B2',alpha=.85,zorder=2);ax.plot([-30,20],[-30,20],ls='--',c='.6',lw=.6,zorder=.2);zero(ax)
    ax.set(xlim=(-30,20),ylim=(-30,20),xlabel='United States maize\nyield anomaly (%)',ylabel='United States soybean\nyield anomaly (%)');title(ax,'c','United States','Maize–soybean · 13 events');ccoords=np.asarray(c.get_offsets()).tolist()
    for j,(sid,name,letter) in enumerate([('LSO×MAIZE','Lesotho maize','d'),('ZAF×MAIZE','South African maize','e'),('AUS×WHEAT','Australian wheat','f')]):
        ax=axs[1,j];r=cases[cases.system_a.eq(sid)].iloc[0]
        for stem,lab,color,marker in series:
            line,=ax.plot([0,1],[r[stem+'_a'],r[stem+'_b']],color=color,marker=marker,ms=3.6,lw=.95,zorder=2)
            case_artists.append(dict(panel=letter,system_id=sid,series=stem,years=[int(r.years_a),int(r.years_b)],values=list(map(float,line.get_ydata()))))
        ax.axhline(0,c='.65',lw=.6,zorder=.2);ax.set(xlim=(-.12,1.12),ylim=(-45,35),xticks=[0,1],xticklabels=[str(int(r.years_a)),str(int(r.years_b))],yticks=[-40,-20,0,20])
        if j==0:ax.set_ylabel('Yield anomaly or contribution\n(% / pp)')
        title(ax,letter,name,str(int(r.years_a))+' and '+str(int(r.years_b)))
    fig.text(.545,.12,'Compared harvest years (discrete events)',ha='center',fontsize=7)
    fig.legend(handles=[Line2D([],[],color=color,marker=marker,ms=3.5,lw=.95,label=lab) for _,lab,color,marker in series],loc='center',bbox_to_anchor=(.545,.065),ncol=3,frameon=False,fontsize=6.1,columnspacing=1.3)
    fig.canvas.draw()
    fig.savefig(O/f'variants/Figure_4_{tag}.png',dpi=300)
    fig.savefig(O/f'variants/Figure_4_{tag}.pdf')
    fig.savefig(O/f'variants/Figure_4_{tag}.svg')
    # Exact panel-a crop from the same 180mm figure, including its new summary key.
    fig.savefig(O/f'variants/Figure_4a_{tag}.png',dpi=600,bbox_inches=matplotlib.transforms.Bbox.from_extents(.005*180/25.4,.498*150/25.4,.36*180/25.4,.96*150/25.4))
    plt.close(fig)
    pd.DataFrame(drawn).to_csv(O/f'qa/{tag}_DRAWN_RECORDS.csv',index=False)
    (O/f'qa/{tag}_ARTISTS.json').write_text(json.dumps(dict(case_artists=case_artists,b=bcoords,c=ccoords,summaries=summaries),indent=2),encoding='utf8')
    Image.open(O/f'variants/Figure_4_{tag}.png').convert('L').save(O/f'qa/{tag}_grayscale.png')
    with fitz.open(O/f'variants/Figure_4_{tag}.pdf') as doc:
        for dpi in [96,150]:doc[0].get_pixmap(dpi=dpi).save(str(O/f'qa/{tag}_{dpi}dpi.png'))
render('A','modelled')
print('Event-weather figure rendered from stored records.')
