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
from rentl_agents.qa import (
    build_qa_summary,
    chunk_qa_lines,
    empty_qa_output,
    format_lines_for_qa_prompt,
    get_scene_summary_for_qa,
    merge_qa_agent_outputs,
    violation_to_qa_issue,
)
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
from rentl_agents.translate import (
    chunk_lines as translate_chunk_lines,
)
from rentl_agents.translate import (
    format_annotated_lines_for_prompt,
    format_glossary_terms,
    format_pretranslation_annotations,
    merge_translated_lines,
    translation_result_to_lines,
)
from rentl_agents.translate import (
    format_lines_for_prompt as translate_format_lines,
)
from rentl_agents.translate import (
    get_scene_summary_for_lines as translate_get_scene_summary,
)
from rentl_agents.wiring import (
    ContextSceneSummarizerAgent,
    EditBasicEditorAgent,
    PretranslationIdiomLabelerAgent,
    QaStyleGuideCriticAgent,
    TranslateDirectTranslatorAgent,
    create_context_agent_from_profile,
    create_edit_agent_from_profile,
    create_pretranslation_agent_from_profile,
    create_qa_agent_from_profile,
    create_translate_agent_from_profile,
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
    "EditBasicEditorAgent",
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
    "QaStyleGuideCriticAgent",
    "SceneValidationError",
    "SchemaResolutionError",
    "StyleGuideLookupTool",
    "TemplateContext",
    "TemplateRenderError",
    "TemplateValidationError",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolResolutionError",
    "TranslateDirectTranslatorAgent",
    "build_qa_summary",
    "chunk_lines",
    "chunk_qa_lines",
    "create_context_agent_from_profile",
    "create_edit_agent_from_profile",
    "create_pretranslation_agent_from_profile",
    "create_qa_agent_from_profile",
    "create_translate_agent_from_profile",
    "discover_agent_profiles",
    "empty_qa_output",
    "extract_template_variables",
    "format_annotated_lines_for_prompt",
    "format_glossary_terms",
    "format_lines_for_prompt",
    "format_lines_for_qa_prompt",
    "format_pretranslation_annotations",
    "format_scene_lines",
    "get_agents_for_phase",
    "get_allowed_variables_for_layer",
    "get_default_agents_dir",
    "get_default_prompts_dir",
    "get_default_registry",
    "get_scene_summary_for_lines",
    "get_scene_summary_for_qa",
    "group_lines_by_scene",
    "idiom_to_annotation",
    "load_agent_profile",
    "load_layer_registry",
    "load_phase_prompt",
    "load_root_prompt",
    "merge_idiom_annotations",
    "merge_qa_agent_outputs",
    "merge_scene_summaries",
    "merge_translated_lines",
    "register_output_schema",
    "render_template",
    "resolve_output_schema",
    "translate_chunk_lines",
    "translate_format_lines",
    "translate_get_scene_summary",
    "translation_result_to_lines",
    "validate_agent_template",
    "validate_scene_input",
    "validate_template",
    "violation_to_qa_issue",
]
