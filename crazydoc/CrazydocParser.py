from docx import Document

from .Observers import (HighlightColor, FontColor, Bold, Italic, UpperCase,
                        LowerCase, Underline)
from .biotools import string_is_sequence


class CrazydocParser:
    """Parser to translate MS-docx documents to Biopython records.

    Examples:
    ---------

    >>> parser = CrazydocParser(['highlight_color', 'font_color'])
    >>> biopython_records = parser.parse_doc_file('example.docx')

    Parameters
    ----------

    observers
      A list of either ``crazydoc.Observer`` objects or observer names in
      ``highlight_color``, ``font_color``, ``bold``, ``italic``,
      ``upper_case``, ``lower_case``, ``underline``.
    """
    observers_dict = {
        _class.name: _class()
        for _class in (HighlightColor, FontColor, Bold, Italic, UpperCase,
                       LowerCase, Underline)
    }

    def __init__(self, observers):
        self.observers = [
            self.observers_dict[o] if isinstance(o, str) else o
            for o in observers
        ]


    def _extract_sequence_names_and_runs(self, doc):
        """Parse the doc, return a list [(sequence_name, sequenceruns), ...]"""
        sequence_name = None
        sequence_paragraphs = []
        reading_sequence = False
        for paragraph in doc.paragraphs:
            if string_is_sequence(paragraph.text):
                if reading_sequence:
                    sequence_paragraphs[-1][1].append(paragraph)
                else:
                    reading_sequence = True
                    sequence_paragraphs.append((sequence_name, [paragraph]))
            else:
                if reading_sequence:
                    sequence_name = None
                    reading_sequence = False
                if paragraph.text.startswith('>'):
                    sequence_name = paragraph.text[1:].strip()
        sequence_paragraphs
        return [
            (name, [run for par in paragraphs for run in par.runs])
            for name, paragraphs in sequence_paragraphs
        ]

    def _msword_runs_to_record(self, runs):
        """Transform a MS Word runs list to a biopython record."""
        records = [
            observer.msword_runs_to_record(runs)
            for observer in self.observers
        ]
        final_record = records[0]
        record_features = {
            (feature.location.start, feature.location.end): feature
            for feature in final_record.features
        }
        for record in records[1:]:
            for feature in record.features:
                location = feature.location.start, feature.location.end
                if location in record_features:
                    qualifiers = record_features[location].qualifiers
                    qualifiers.update(feature.qualifiers)
                else:
                    final_record.features.append(feature)
                    record_features[location] = feature
        return final_record



    def parse_doc_file(self, filepath=None, doc=None):
        """Return a list of records, 1 for each sequence contained in the docx.

        Parameters
        ----------

        filepath
          A path to a docx file

        doc
          A python-docx Document object, which can be provided instead of the
          file path.
        """
        if doc is None:
            doc = Document(filepath)
        records = []
        for name, runs in self._extract_sequence_names_and_runs(doc):
            record = self._msword_runs_to_record(runs)
            if name is not None:
                record.id = name
                record.name = name.replace(' ', '_')
            for observer in self.observers:
                observer.process_record_features(record)
            records.append(record)
        return records