"""Professional NLE tools for AI Director.

The modules here are deliberately UI-independent so the editor can grow without
coupling timeline logic to Qt.
"""
from .editor_engine import ProfessionalEditEngine, EditResult
from .markers import Marker, MarkerStore
from .media_relink import MediaRelinker, RelinkResult
from .render_queue import RenderJob, RenderQueue
from .color import ColorGrade, color_grade_fragment
from .editing_workspace import EditingWorkspace, EDIT_MODES

__all__ = ["ProfessionalEditEngine","EditResult","Marker","MarkerStore","MediaRelinker","RelinkResult","RenderJob","RenderQueue","ColorGrade","color_grade_fragment","EditingWorkspace","EDIT_MODES"]
from .advanced_nle import (CompoundClip, AdjustmentLayer, ProxyAsset, ProxyManager,
                           MulticamAngle, CameraSwitch, MulticamSequence, AdvancedEditorState)

# Smart Proxy Intelligence is kept in a separate package to avoid coupling the NLE model.
