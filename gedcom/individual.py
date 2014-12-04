from .register import register_tag
from .element import Element

@register_tag("INDI")
class Individual(Element):

    """Represents and INDI (Individual) element."""

    @property
    def parents(self):
        """
        Return list of parents of this person.

        NB: There may be 0, 1, 2, 3, ... elements in this list.

        :returns: List of Individual's
        """
        if 'FAMC' in self:
            family_as_child_id = self['FAMC'].value
            family = self.get_by_id(family_as_child_id)
            if not any(child.value == self.id for child in family.get_list("CHIL")):
                # raise Exception("Invalid family", family, self)
                pass
            parents = family.partners
            parents = [p.as_individual() for p in parents]
            return parents
        else:
            return []

    @property
    def name(self):
        """
        Return this person's name.

        :returns: (firstname, lastname)
        """
        name_tag = self['NAME']

        if isinstance(name_tag, list):
            # We have more than one name, get the preferred name
            # Don't assume it's the first
            for name in name_tag:

                if 'TYPE' in name:
                    pass
                else:
                    preferred_name = name
                    break

        else:
            # We've only one name
            preferred_name = name_tag

        if preferred_name.value in ('', None):
            first = preferred_name['GIVN'].value
            last = preferred_name['SURN'].value
        else:
            first, last, dud = preferred_name.value.split("/")
            first = first.strip()
            last = last.strip()

        return first, last

    @property
    def aka(self):
        '''
        Return a list of 'also known as' names.
        '''

        aka_list = []
        name_tag = self['NAME']

        if isinstance(name_tag, list):
            # We have more than one name, get the aka names
            for name in name_tag:

                if 'TYPE' in name and name['TYPE'].value.lower() == 'aka':
                    if name.value in ('', None):
                        first = name['GIVN'].value
                        last = name['SURN'].value
                    else:
                        first, last, dud = name.value.split("/")
                        first = first.strip()
                        last = last.strip()
                    aka_list.append((first, last))

        return aka_list

    @property
    def birth(self):
        """Class representing the birth of this person."""
        return self['BIRT']

    @property
    def death(self):
        """Class representing the death of this person."""
        return self['DEAT']

    @property
    def sex(self):
        """
        Return the sex of this person, as the string 'M' or 'F'.

        NB: This should probably support more sexes/genders.

        :rtype: str
        """
        return self['SEX'].value

    @property
    def gender(self):
        """
        Return the sex of this person, as the string 'M' or 'F'.

        NB: This should probably support more sexes/genders.

        :rtype: str
        """
        return self['SEX'].value

    @property
    def father(self):
        """
        Calculate and return the individual represenating the father of
        this person.

        Returns `None` if none found.

        :return: the father, or `None` if not in file.
        :raises NotImplementedError: If it cannot figure out who's the father.
        :rtype: :py:class:`Individual`
        """
        male_parents = [p for p in self.parents if p.is_male]
        if len(male_parents) == 0:
            return None
        elif len(male_parents) == 1:
            return male_parents[0]
        elif len(male_parents) > 1:
            raise NotImplementedError()

    @property
    def mother(self):
        """
        Calculate and return the individual represenating the mother of
        this person.

        Returns `None` if none found.

        :return: the mother, or `None` if not in file.
        :raises NotImplementedError: If it cannot figure out who's the mother.
        :rtype: :py:class:`Individual`
        """
        female_parents = [p for p in self.parents if p.is_female]
        if len(female_parents) == 0:
            return None
        elif len(female_parents) == 1:
            return female_parents[0]
        elif len(female_parents) > 1:
            raise NotImplementedError()

    @property
    def is_female(self):
        """ Return True iff this person is recorded as female. """
        return self.sex.lower() == 'f'

    @property
    def is_male(self):
        """ Return True iff this person is recorded as male. """
        return self.sex.lower() == 'm'

    def set_sex(self, sex):
        """
        Set the sex for this person.

        :param str sex: 'M' or 'F' for male or female resp.
        :raises TypeError: if `sex` is invalid
        """
        sex = sex.upper()
        if sex not in ['M', 'F']:
            raise TypeError("Currently only support M or F")
        try:
            sex_node = self['SEX']
            sex_node.value = sex
        except IndexError:
            self.add_child_element(self.gedcom_file.element("SEX", value=sex))

    @property
    def title(self):
        try:
            return self['TITL'].value
        except:
            return None

