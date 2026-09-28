export const wagtailImprintImageSelector = "figure.imprint-visual > img";

export function editorialImprintImageCheck(profile, state) {
  if (profile !== "wagtail" || !state.present) return null;

  return {
    name: "imprint: configured editorial image replaces organic SMIL",
    pass: state.count === 1 && state.visible && state.complete && state.naturalWidth > 0 && !state.organicShapePresent && state.smilElementCount === 0,
    detail: `count=${state.count}; visible=${state.visible}; complete=${state.complete}; naturalWidth=${state.naturalWidth}; organic SVG present=${state.organicShapePresent}; SMIL elements=${state.smilElementCount}`,
  };
}
