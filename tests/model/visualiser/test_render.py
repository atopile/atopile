from atopile.model.model import Model
from atopile.visualizer.render import build_view

def test_build_from_root(dummy_model: Model):
    assert build_view(dummy_model, "dummy_file.ato") == \
        {
            'name': 'dummy_file.ato',
            'type': 'file',
            'fields': {},
            'blocks': [
                {
                    'name': 'dummy_module',
                    'type': 'module',
                    'fields': {},
                    'blocks': [
                        {
                            'name': 'dummy_comp0',
                            'type': 'component',
                            'fields': {},
                            'blocks': [],
                            'pins': [
                                {
                                    'name': 'spare_sig',
                                    'fields': {}
                                },
                                {
                                    'name': 'sig0',
                                    'fields': {}
                                },
                                {
                                    'name': 'sig1',
                                    'fields': {}
                                }
                            ],
                            'links': [
                                {
                                    'source': 'p0',
                                    'target': 'sig0'
                                },
                                {
                                    'source': 'p1',
                                    'target': 'sig1'
                                },
                                {
                                    'source': 'sig0',
                                    'target': 'sig1'
                                }
                            ],
                            'instance_of': None
                        },
                        {
                            'name': 'dummy_comp1',
                            'type': 'component',
                            'fields': {},
                            'blocks': [],
                            'pins': [
                                {
                                    'name': 'spare_sig',
                                    'fields': {}
                                },
                                {
                                    'name': 'sig0',
                                    'fields': {}
                                },
                                {
                                    'name': 'sig1',
                                    'fields': {}
                                }
                            ],
                            'links': [
                                {
                                    'source': 'p0',
                                    'target': 'sig0'
                                },
                                {
                                    'source': 'p1',
                                    'target': 'sig1'
                                }
                            ],
                            'instance_of': None
                        }
                    ],
                    'pins': [
                        {
                            'name': 'top_sig',
                            'fields': {}
                        }
                    ],
                    'links': [
                        {
                            'source': 'top_sig',
                            'target': 'dummy_comp1.sig1'
                        },
                        {
                            'source': 'dummy_comp0.spare_sig',
                            'target': 'dummy_comp1.spare_sig'
                        }
                    ],
                    'instance_of': None
                }
            ],
            'pins': [],
            'links': [],
            'instance_of': None
        }
