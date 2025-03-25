from dataclasses import dataclass


@dataclass(frozen=True)
class Center:
    """
    Represents a clinical center participating in the study.

    Each center has its own MRI machine with specific acquisition parameters,
    which requires computing center-specific DTI reference values.
    """

    id: int
    name: str

    def __repr__(self):
        return f"Center(id={self.id}, name={self.name})"
