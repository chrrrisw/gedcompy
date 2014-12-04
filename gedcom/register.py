from .element import Element

tags_to_classes = {}


def register_tag(tag):
    """ Internal class decorator to mark a python class as to be the handler for this tag.  """
    def classdecorator(klass):
        global tags_to_classes
        tags_to_classes[tag] = klass
        klass.default_tag = tag
        return klass
    return classdecorator


def class_for_tag(tag):
    """
    Return the class object for this `tag`
    :param str tag: tag (e.g. INDI)
    :rtype: class (Element or something that's a subclass)
    """
    global tags_to_classes
    return tags_to_classes.get(tag, Element)


def line_to_element(**line_dict):
    """
    Return an instance of :py:class:`Element` (or subclass) based on these parsed out values from :py:const:`line_regex`.

    :rtype: Element or subclass
    """
    return class_for_tag(line_dict['tag'])(**line_dict)

