"""Line alignment for matching source and reference translations."""

from rentl_schemas.io import SourceLine


class AlignedLinePair:
    """A pair of aligned source and reference lines."""

    def __init__(
        self,
        source: SourceLine,
        reference: SourceLine | None = None,
    ) -> None:
        """Initialize an aligned line pair.

        Args:
            source: Source language line
            reference: Optional reference translation line
        """
        self.source = source
        self.reference = reference


class LineAligner:
    """Aligns source and reference translation lines by scene/line ID."""

    def align_by_id(
        self,
        source_lines: list[SourceLine],
        reference_lines: list[SourceLine],
    ) -> list[AlignedLinePair]:
        """Align source and reference lines by matching line_id.

        Args:
            source_lines: Source language lines
            reference_lines: Reference translation lines

        Returns:
            List of aligned line pairs (reference may be None if no match found)
        """
        # Build a lookup dict for reference lines
        ref_lookup = {line.line_id: line for line in reference_lines}

        # Align by line_id
        aligned: list[AlignedLinePair] = []
        for source_line in source_lines:
            reference = ref_lookup.get(source_line.line_id)
            aligned.append(AlignedLinePair(source=source_line, reference=reference))

        return aligned

    def align_by_position(
        self,
        source_lines: list[SourceLine],
        reference_lines: list[SourceLine],
    ) -> list[AlignedLinePair]:
        """Align source and reference lines by position in list.

        Args:
            source_lines: Source language lines
            reference_lines: Reference translation lines

        Returns:
            List of aligned line pairs (reference may be None if lists have
            different lengths)
        """
        aligned: list[AlignedLinePair] = []
        for idx, source_line in enumerate(source_lines):
            reference = reference_lines[idx] if idx < len(reference_lines) else None
            aligned.append(AlignedLinePair(source=source_line, reference=reference))

        return aligned
