"""Agent runtime scaffold for rentl phase agents."""

from rentl_agents.context import (
    SceneValidationError,
    format_scene_lines,
    group_lines_by_scene,
    merge_scene_summaries,
    validate_scene_input,
)
from rentl_agents.factory import AgentConfig, AgentFactory
from rentl_agents.harness import AgentHarness, AgentHarnessConfig
from rentl_agents.layers import (
    LayerLoadError,
    PromptComposer,
    PromptLayerRegistry,
    load_layer_registry,
    load_phase_prompt,
    load_root_prompt,
)
from rentl_agents.pretranslation import (
    chunk_lines,
    format_lines_for_prompt,
    get_scene_summary_for_lines,
    idiom_to_annotation,
    merge_idiom_annotations,
)
from rentl_agents.profiles import (
    AgentProfileLoadError,
    SchemaResolutionError,
    ToolResolutionError,
    discover_agent_profiles,
    get_agents_for_phase,
    load_agent_profile,
    register_output_schema,
    resolve_output_schema,
)
from rentl_agents.prompts import PromptRenderer, PromptTemplate
from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.templates import (
    TemplateContext,
    TemplateRenderError,
    TemplateValidationError,
    extract_template_variables,
    get_allowed_variables_for_layer,
    render_template,
    validate_agent_template,
    validate_template,
)
from rentl_agents.tools import (
    AgentTool,
    AgentToolProtocol,
    ContextLookupTool,
    GlossarySearchTool,
    StyleGuideLookupTool,
)
from rentl_agents.tools.game_info import GameInfoTool, ProjectContext
from rentl_agents.tools.registry import (
    ToolNotFoundError,
    ToolRegistry,
    get_default_registry,
)
from rentl_agents.wiring import (
    ContextSceneSummarizerAgent,
    PretranslationIdiomLabelerAgent,
    create_context_agent_from_profile,
    create_pretranslation_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
)

__all__ = [
    "AgentConfig",
    "AgentFactory",
    "AgentHarness",
    "AgentHarnessConfig",
    "AgentProfileLoadError",
    "AgentTool",
    "AgentToolProtocol",
    "ContextLookupTool",
    "ContextSceneSummarizerAgent",
    "GameInfoTool",
    "GlossarySearchTool",
    "LayerLoadError",
    "PretranslationIdiomLabelerAgent",
    "ProfileAgent",
    "ProfileAgentConfig",
    "ProjectContext",
    "PromptComposer",
    "PromptLayerRegistry",
    "PromptRenderer",
    "PromptTemplate",
    "SceneValidationError",
    "SchemaResolutionError",
    "StyleGuideLookupTool",
    "TemplateContext",
    "TemplateRenderError",
    "TemplateValidationError",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolResolutionError",
    "chunk_lines",
    "create_context_agent_from_profile",
    "create_pretranslation_agent_from_profile",
    "discover_agent_profiles",
    "extract_template_variables",
    "format_lines_for_prompt",
    "format_scene_lines",
    "get_agents_for_phase",
    "get_allowed_variables_for_layer",
    "get_default_agents_dir",
    "get_default_prompts_dir",
    "get_default_registry",
    "get_scene_summary_for_lines",
    "group_lines_by_scene",
    "idiom_to_annotation",
    "load_agent_profile",
    "load_layer_registry",
    "load_phase_prompt",
    "load_root_prompt",
    "merge_idiom_annotations",
    "merge_scene_summaries",
    "register_output_schema",
    "render_template",
    "resolve_output_schema",
    "validate_agent_template",
    "validate_scene_input",
    "validate_template",
]
