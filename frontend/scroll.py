# frontend/scroll.py
from streamlit.components.v1 import html as comp_html

def scroll_smooth_once():
    """
    Same as scroll_once, but smooth. Use sparingly (e.g., at start/end),
    not on every chunk, to avoid browser 'tail' inertia.
    """
    comp_html("""
    <script>
    (function(){
      const d = window.parent.document;
      const r = d.querySelector('section[data-testid="stMain"]')
              || d.scrollingElement || d.documentElement || d.body;
      if (!r) return;
      try {
        if (r.scrollTo) r.scrollTo({top: r.scrollHeight, behavior:'smooth'});
        else r.scrollTop = r.scrollHeight;
      } catch(e){
        const de = d.scrollingElement || d.documentElement || d.body;
        window.parent.scrollTo({top: de.scrollHeight, behavior:'smooth'});
      }
    })();
    </script>
    """, height=0, width=0)
