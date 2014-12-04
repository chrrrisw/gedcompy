"""
Library for reading and writing GEDCOM files.

https://en.wikipedia.org/wiki/GEDCOM
"""
import re
import os.path
import six
from .register import register_tag, line_to_element, class_for_tag
from .element import Element
from .individual import Individual

__version__ = "0.1.0"

line_format = re.compile("^(?P<level>[0-9]+) ((?P<id>@[a-zA-Z0-9]+@) )?(?P<tag>[_A-Z0-9]+)( (?P<value>.*))?$")


class GedcomFile(object):

    """ Represents a GEDCOM file.  """

    def __init__(self):
        """Instanciate a GEDCOM object."""
        self.root_elements = []
        self.pointers = {}
        self.next_free_id = 1

    def __repr__(self):
        """String represenation of GEDCOM. For internal debugging purposes only."""
        return "GedcomFile(\n" + ",\n".join(repr(c) for c in self.root_elements) + ")"

    def __getitem__(self, key):
        """
        Return the element that has this pointer/id in this file.

        :param string key: Pointer for object (e.g. "@I33@")
        :returns: Element with this id
        :rtype: :py:class:`Element`
        :raises KeyError: If key is not in this file
        """
        return self.pointers[key]

    def add_element(self, element):
        """
        Add an Element to this file.

        If element.level is unset, it'll presume it's a top level element, and set the level and id appropriately.

        :param :py:class:`Element` element: Element to add
        """
        if element.level is None:
            # Need to figure out an element
            if not (isinstance(element, Individual) or isinstance(element, Family)):
                raise TypeError()
            element.level = 0
            element.set_levels_downward()

            # create pointer
            if isinstance(element, Individual):
                prefix = 'I'
            elif isinstance(element, Family):
                prefix = 'F'
            else:
                raise NotImplementedError()

            for step in range(1, 1000000):
                potential_id = "@{prefix}{num}@".format(prefix=prefix, num=self.next_free_id)
                if potential_id in self.pointers:
                    # this number is taken, increase
                    self.next_free_id += 1
                else:
                    # Found a free id
                    element.id = potential_id
                    self.next_free_id += 1
                    break
            else:
                # Tried 1,000,000 times and didn't have a free id? weird!
                # prevents an infinite loop
                raise Exception("Ran out of ids?")

        element.gedcom_file = self
        if element.id:
            self.pointers[element.id] = element
        if element.level == 0:
            self.root_elements.append(element)

    @property
    def individuals(self):
        """
        Iterator of all Individual's in this file.

        :returns: iterator of Individual's
        :rtype: iterator
        """
        return (i for i in self.root_elements if isinstance(i, Individual))

    @property
    def families(self):
        """
        Iterator of all Family's in this file.

        :returns: iterator of Families's
        :rtype: iterator
        """
        return (i for i in self.root_elements if isinstance(i, Family))

    def gedcom_lines(self):
        """
        Iterator that returns the lines in this file.

        :returns: iterator over lines
        :rtype: iterator
        """
        self.ensure_header_trailer()
        self.ensure_levels()
        for el in self.root_elements:
            for line in el.gedcom_lines():
                yield line

    def gedcom_lines_as_string(self):
        """
        Return this file as a string.

        :returns: Full encoded text of this file
        :rtype: string
        """
        return "\n".join(self.gedcom_lines())

    def save(self, fileout):
        """
        Saves the contents of this GEDCOM file to specified filename or file-like object.

        :param fileout: Filename or open file-like object to save this to.
        :raises Exception: if the filename exists
        """
        if isinstance(fileout, six.string_types):
            if os.path.exists(fileout):
                # TODO better exception
                raise Exception("File exists")
            else:
                with open(fileout, "w") as fp:
                    return self.save(fp)

        for line in self.gedcom_lines():
            fileout.write(line.encode("utf8"))
            fileout.write("\n")

    def ensure_header_trailer(self):
        """
        If GEDCOM file does not have a header (HEAD) or trailing element (TRLR), it will be added. If those exist they won't be added.

        Call this method to ensure the file has these required elements.
        """
        if len(self.root_elements) == 0 or self.root_elements[0].tag != 'HEAD':
            # add header
            head_element = self.element('HEAD', level=0, value='')
            source = self.element("SOUR")
            source.add_child_element(self.element("NAME", value="gedcompy"))
            source.add_child_element(self.element("VERS", value=__version__))
            head_element.add_child_element(source)
            head_element.add_child_element(self.element("CHAR", value="UNICODE"))

            gedcom_format = self.element("GEDC")
            gedcom_format.add_child_element(self.element("VERS", value="5.5"))
            gedcom_format.add_child_element(self.element("FORM", value="LINEAGE-LINKED"))
            head_element.add_child_element(gedcom_format)

            head_element.set_levels_downward()
            self.root_elements.insert(0, head_element)
        if len(self.root_elements) == 0 or self.root_elements[-1].tag != 'TRLR':
            # add trailer
            self.root_elements.append(self.element('TRLR', level=0, value=''))

    def ensure_levels(self):
        """
        Ensures that the levels for all elements in this file are sensible.

        Sets the :py:attr:`Element.level` of all root elements to 0, and calls
        :py:meth:`Element.set_levels_downward` on each one.
        """
        for root_el in self.root_elements:
            root_el.level = 0
            root_el.set_levels_downward()

    def element(self, tag, **kwargs):
        """
        Return a new Element that is in this file.
        :param str tag: tag name for this object
        :param **kwargs: Passed to Element constructor
        :rtype: Element or subclass based on `tag`
        """
        klass = class_for_tag(tag)
        return klass(gedcom_file=self, tag=tag, **kwargs)

    def individual(self, **kwargs):
        return self.element("INDI", **kwargs)

    def family(self, **kwargs):
        return self.element("FAM", **kwargs)


@register_tag("FAM")
class Family(Element):

    """Represents a family 'FAM' tag."""

    @property
    def partners(self):
        """
        Return list of partners in this marriage. all HUSB/WIFE child elements. Not dereferenced
        :rtype: list of Husband or Wives
        """
        return self.get_list("HUSB") + self.get_list("WIFE")


class Spouse(Element):

    """Generic base class for HUSB/WIFE."""

    def as_individual(self):
        """
        Return the :py:class:`Individual` for this object.

        :returns: the individual
        :rtype: :py:class:`Individual`
        :raises KeyError: if id/pointer not found in the file.
        """
        return self.gedcom_file[self.value]


@register_tag("HUSB")
class Husband(Spouse):

    """Represents pointer to a husband in a family."""

    pass


@register_tag("WIFE")
class Wife(Spouse):

    """Represents pointer to a husband in a family."""

    pass


class Event(Element):

    """Generic base class for events, like :py:class:`Birth` (BIRT) etc."""

    @property
    def date(self):
        """
        Get the Date of this event, from the 'DATE' tagged child element.

        :returns: date value
        :rtype: string
        :raises KeyError: if there is no DATE sub-element
        """
        return self['DATE'].value

    @property
    def place(self):
        """
        Get the place of this event, from the 'PLAC' tagged child element.

        :returns: date value
        :rtype: string
        :raises KeyError: if there is no PLAC sub-element
        """
        return self['PLAC'].value


@register_tag("BIRT")
class Birth(Event):

    """Represents a birth (BIRT)."""

    pass


@register_tag("DEAT")
class Death(Event):

    """Represents a death (DEAT)."""

    pass


@register_tag("MARR")
class Marriage(Event):

    """Represents a marriage (MARR)."""

    pass


@register_tag("NOTE")
class Note(Element):

    """Represents a note (NOTE)."""

    @property
    def full_text(self):
        result = "" + self.value or ''

        for cons in self.child_elements:
            if cons.tag == 'CONT':
                result += "\n"
                result += cons.value or ''
            elif cons.tag == 'CONC':
                result += cons.value or ''
            else:
                raise ValueError("Full text can only consist of CONS and CONT")

        return result


def parse_filename(filename):
    """
    Parse filename and return GedcomFile.

    :param string filename: Filename to parse
    :returns: GedcomFile instance
    """
    with open(filename, 'r') as fp:
        return __parse(fp.readlines())


def parse_string(string):
    """
    Parse filename and return GedcomFile.

    :param str string: Filename to parse
    :returns: GedcomFile instance
    """
    return __parse(string.split("\n"))


def parse_fp(file_fp):
    """
    Parse file and return GedcomFile.

    :param filehandle file_fp: open file handle for input
    :returns: GedcomFile
    """
    return __parse(file_fp.readlines())


def parse(obj):
    """
    Parse and return this object, if it's a file.

    If it's a filename, it calls :py:func:`parse_filename`,
    for file-like objects, :py:mod:`parse_fp`,
    for strings, calls :py:mod:`parse_string`.

    :param obj: filename, open file-like object or string contents of GEDCOM file
    :returns: GedcomFile
    """
    if isinstance(obj, six.string_types):
        # Sanity check, presumes anything > 1KB could not be a filename
        if len(obj) <= 1024 and os.path.exists(obj):
            return parse_filename(obj)
        else:
            return parse_string(obj)
    else:
        return parse_fp(obj)


def __parse(lines_iter):
    current_level = 0
    level_to_obj = {}
    gedcom_file = GedcomFile()

    for linenum, line in enumerate(lines_iter):
        line = line.strip()
        if line == '':
            continue
        match = line_format.match(line)
        if not match:
            raise NotImplementedError(line)

        level = int(match.groupdict()['level'])

        if level == 0:
            parent = None
        else:
            level_to_obj = dict((l, obj) for l, obj in level_to_obj.items() if l < level)
            parent = level_to_obj[level - 1]

        element = line_to_element(
            level=level,
            parent=parent,
            tag=match.groupdict()['tag'],
            value=match.groupdict()['value'],
            id=match.groupdict()['id'])

        level_to_obj[level] = element
        element.gedcom_file = gedcom_file
        gedcom_file.add_element(element)

    return gedcom_file
