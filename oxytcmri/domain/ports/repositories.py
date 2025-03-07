from typing import List, Optional, Protocol
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center


class SubjectRepository(Protocol):
    def find_subjects_by_center(self, 
                               center: Center, 
                               subject_type: Optional[SubjectType] = None) -> List[Subject]:
        """
        Find subjects for a given center, optionally filtered by type.
        
        Parameters
        ----------
        center : Center
            The center to find subjects for
        subject_type : Optional[SubjectType], default=None
            If provided, only return subjects of this type
            
        Returns
        -------
        List[Subject]
            List of matching subjects
        """
        pass