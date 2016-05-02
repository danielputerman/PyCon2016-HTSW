"""Provides classes for recording webdriver actions"""
import json
import metaprog_utils
from selenium.webdriver.common.by import By
from metaprog_utils import create_proxy_interface, create_proxy_property


# noinspection PyAttributeOutsideInit
class Recorder(object):
    """A class for handling the recording"""

    def start(self, driver):
        self._pages = []
        self._current_page = {}
        return RecordingWebDriver(self, driver)

    def close(self):
        self._pages.append(self._current_page)

    def on_navigate_to_url(self, url):
        if self._current_page:
            self._pages.append(self._current_page)

        self._current_page = {'url': url, 'recorded_events': []}

    @staticmethod
    def _get_event_location(element):
        element_location = element.location
        element_size = element.size
        return {'x': element_location['x'] + (element_size['width'] / 2),
                'y': element_location['y'] + (element_size['height'] / 2)}

    def _add_event(self, element, event):
        event['location'] = Recorder._get_event_location(element)
        self._current_page['recorded_events'].append(event)

    def on_click(self, element):
        self._add_event(element, {'event_type': 'click'})

    def on_send_keys(self, element, text):
        self._add_event(element, {'event_type': 'send_keys', 'text': text})

    def export(self):
        return json.dumps(self._pages)


class RecordingWebElement(object):
    """
    A wrapper for selenium web element. This enables us to be notified about actions/events for
    this element.
    """
    _METHODS_TO_REPLACE = ['find_element', 'find_elements']

    # Properties require special handling since even testing if they're callable "activates"
    # them, which makes copying them automatically a problem.
    _READONLY_PROPERTIES = ['tag_name', 'text', 'location_once_scrolled_into_view', 'size',
                            'location', 'parent', 'id', 'rect', 'screenshot_as_base64', 'screenshot_as_png']

    def __init__(self, recorder, driver, element):
        self.element = element
        self._recorder = recorder
        self._driver = driver
        # MONKEY PATCH ALERT! Replacing implementation of the underlying driver with ours. We'll put the original
        # methods back before destruction.
        self._original_methods = {}
        for method_name in self._METHODS_TO_REPLACE:
            self._original_methods[method_name] = getattr(element, method_name)
            setattr(element, method_name, getattr(self, method_name))

        # Copies the web element's interface
        create_proxy_interface(self, element, self._READONLY_PROPERTIES)
        # Setting properties
        for attr in self._READONLY_PROPERTIES:
            setattr(self.__class__, attr, create_proxy_property(attr, 'element'))

    def find_element(self, by=By.ID, value=None):
        """
        Returns a WebElement denoted by "By".
        """
        # Get element from the original implementation of the underlying driver.
        element = self._original_methods['find_element'](by, value)
        # Wrap the element.
        if element:
            element = RecordingWebElement(self._recorder, self._driver, element)
        return element

    def find_elements(self, by=By.ID, value=None):
        """
        Returns a list of web elements denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        elements_list = self._original_methods['find_elements'](by, value)
        # Wrap all returned elements.
        if elements_list:
            updated_list = []
            for element in elements_list:
                updated_list.append(RecordingWebElement(self._recorder, self._driver, element))
            elements_list = updated_list
        return elements_list

    def click(self):
        self._recorder.on_click(self)
        self.element.click()
        self._recorder.on_navigate_to_url(self._driver.current_url)

    def send_keys(self, *value):
        text = u''
        for val in value:
            if isinstance(val, int):
                val = val.__str__()
            text += val.encode('utf-8').decode('utf-8')
        self._recorder.on_send_keys(self, text)
        self.element.send_keys(*value)


class RecordingWebDriver(object):
    """
    A wrapper for selenium web driver which creates wrapped elements, and notifies us about
    events / actions.
    """
    # Properties require special handling since even testing if they're callable "activates"
    # them, which makes copying them automatically a problem.
    _READONLY_PROPERTIES = ['application_cache', 'current_url', 'current_window_handle',
                            'desired_capabilities', 'log_types', 'name', 'page_source', 'title',
                            'window_handles', 'switch_to', 'mobile', 'application_cache', 'log_types']
    _SETTABLE_PROPERTIES = ['orientation', 'file_detector']

    def __init__(self, recorder, driver):
        self._recorder = recorder
        self.driver = driver

        # Creating the rest of the driver interface by simply forwarding it to the underlying
        # driver.
        metaprog_utils.create_proxy_interface(self, driver,
                                              self._READONLY_PROPERTIES + self._SETTABLE_PROPERTIES)

        for attr in self._READONLY_PROPERTIES:
            if not hasattr(self.__class__, attr):
                setattr(self.__class__, attr, metaprog_utils.create_proxy_property(attr, 'driver'))
        for attr in self._SETTABLE_PROPERTIES:
            if not hasattr(self.__class__, attr):
                setattr(self.__class__, attr, metaprog_utils.create_proxy_property(attr, 'driver', True))

    def get(self, url):
        self._recorder.on_navigate_to_url(url)
        return self.driver.get(url)

    def find_element(self, by=By.ID, value=None):
        """
        Returns a WebElement denoted by "By".
        """
        # Get element from the original implementation of the underlying driver.
        element = self.driver.find_element(by, value)
        # Wrap the element.
        if element:
            element = RecordingWebElement(self._recorder, self, element)
        return element

    def find_elements(self, by=By.ID, value=None):
        """
        Returns a list of web elements denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        elements_list = self.driver.find_elements(by, value)
        # Wrap all returned elements.
        if elements_list:
            updated_results = []
            for element in elements_list:
                updated_results.append(RecordingWebElement(self._recorder, self, element))
            elements_list = updated_results
        return elements_list

    def find_element_by_id(self, id_):
        return self.find_element(by=By.ID, value=id_)

    def find_elements_by_id(self, id_):
        return self.find_elements(by=By.ID, value=id_)

    def find_element_by_xpath(self, xpath):
        return self.find_element(by=By.XPATH, value=xpath)

    def find_elements_by_xpath(self, xpath):
        return self.find_elements(by=By.XPATH, value=xpath)

    def find_element_by_link_text(self, link_text):
        return self.find_element(by=By.LINK_TEXT, value=link_text)

    def find_elements_by_link_text(self, text):
        return self.find_elements(by=By.LINK_TEXT, value=text)

    def find_element_by_partial_link_text(self, link_text):
        return self.find_element(by=By.PARTIAL_LINK_TEXT, value=link_text)

    def find_elements_by_partial_link_text(self, link_text):
        return self.find_elements(by=By.PARTIAL_LINK_TEXT, value=link_text)

    def find_element_by_name(self, name):
        return self.find_element(by=By.NAME, value=name)

    def find_elements_by_name(self, name):
        return self.find_elements(by=By.NAME, value=name)

    def find_element_by_tag_name(self, name):
        return self.find_element(by=By.TAG_NAME, value=name)

    def find_elements_by_tag_name(self, name):
        return self.find_elements(by=By.TAG_NAME, value=name)

    def find_element_by_class_name(self, name):
        return self.find_element(by=By.CLASS_NAME, value=name)

    def find_elements_by_class_name(self, name):
        return self.find_elements(by=By.CLASS_NAME, value=name)

    def find_element_by_css_selector(self, css_selector):
        return self.find_element(by=By.CSS_SELECTOR, value=css_selector)

    def find_elements_by_css_selector(self, css_selector):
        return self.find_elements(by=By.CSS_SELECTOR, value=css_selector)

