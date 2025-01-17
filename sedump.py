# Copyright 2015 Fernand Lone Sang (Ge0n0sis)
#
# This file is part of SETools.
#
# SETools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# SETools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SETools.  If not, see <http://www.gnu.org/licenses/>.
#

import setools

from setools.policyrep import terule
from setools.policyrep import exception

class SELinuxPolicyDump(setools.SELinuxPolicy):
    """Overloaded SELinuxPolicy"""

    def __str__(self):
        """Output statements in an human readable and compiler ready format."""

        sort = True

        def cond_sort(value):
            """Helper function to sort values according to the sort parameter"""
            return value if not sort else sorted(value)

        def comment(value):
            """Helper function to format comments"""
            comment = ''.join("# {0}\n".format(x) for x in value.splitlines())
            return "#\n{0}#\n\n".format(comment)

        stmt = ""

        # security object classes
        stmt += comment("Define the security object classes")
        for class_ in cond_sort(self.classes()):
            stmt += "class {0}\n".format(class_)
        stmt += "\n"

        # initial security identifiers
        stmt += comment("Define the initial security identifiers")
        for sid_ in cond_sort(self.initialsids()):
            stmt += "sid {0}\n".format(sid_)
        stmt += "\n"

        # access vectors
        stmt += comment("Define common prefixes for access vectors")
        for common_ in cond_sort(self.commons()):
            stmt += "{0}\n\n".format(common_.statement())

        stmt += comment("Define the access vectors")
        for class_ in cond_sort(self.classes()):
            stmt += "{0}\n{1}".format(class_.statement(), "\n" if len(class_.perms) > 0 else "")

        # define MLS sensitivities, categories and levels
        stmt += comment("Define MLS sensitivities, categories and levels")
        for sensitivity_ in cond_sort(self.sensitivities()):
            stmt += "{0}\n".format(sensitivity_.statement())
        stmt += "\n"

        sensitivities_ = ["{0}".format(x) for x in sorted(self.sensitivities())]
        stmt += "dominance {{ {0} }}\n\n".format(', '.join(sensitivities_))

        for category_ in cond_sort(self.categories()):
            stmt += "category {0};\n".format(category_)
        stmt += "\n"
        for level_ in cond_sort(self.levels()):
            stmt += "{0}\n".format(level_.statement())
        stmt += "\n"

        # define MLS policy constraints
        stmt += comment("Define MLS policy constraints")
        for mlscontrain_ in cond_sort(self.constraints()):
            stmt += "{0}\n".format(mlscontrain_.statement())
        stmt += "\n"

        # define policy cap
        stmt += comment("Define policy capabilities")
        for policycap_ in cond_sort(self.polcaps()):
            stmt += "{0}\n".format(policycap_.statement())
        stmt += "\n"

        # define type attributes
        stmt += comment("Define attribute identifiers")
        for attribute_ in cond_sort(self.typeattributes()):
            stmt += "{0}\n".format(attribute_.statement())
        stmt += "\n"

        # define types, aliases and attributes
        stmt += comment("Define type identifiers")
        for type_ in cond_sort(self.types()):
            stmt += "{0}\n".format(type_.statement())
        stmt += "\n"

        # define booleans
        stmt += comment("Define booleans")
        for bool_ in cond_sort(self.bools()):
            stmt += "{0}\n".format(bool_.statement())
        stmt += "\n"

        # define type enforcement rules
        stmt += comment("Define type enforcement rules")
        for terule_ in cond_sort(self.terules()):
            # NOTE: the following is a rip of setools/policyrep/terule
            # stmt += "{0}\n".format(terule_.statement())
            rule_ = ""

            # allowxperm rules
            if isinstance(terule_, terule.AVRuleXperm):
                rule_ += "{0.ruletype} {0.source} {0.target}:{0.tclass} {0.xperm_type}".format(terule_)
                perms = terule_.perms

                # generate short permission notation
                if perms.ranges() > 1:
                    rule_ += " {{ {0} }};".format(perms)
                else:
                    rule_ += " {0};".format(perms)
            # allow/dontaudit/auditallow/neverallow rules
            elif isinstance(terule_, terule.AVRule):
                rule_ += "{0.ruletype} {0.source} {0.target}:{0.tclass}".format(terule_)
                perms = terule_.perms
                assert(type(perms) == set)

                if len(perms) > 1:
                    perms = [str(x) for x in perms]
                    rule_ += " {{ {0} }};".format(' '.join(perms))
                else:
                    # convert to list since sets cannot be indexed
                    rule_ += " {0};".format(list(perms)[0])
            # type_* type enforcement rules
            elif isinstance(terule_, terule.TERule):
                rule_ += "{0.ruletype} {0.source} {0.target}:{0.tclass} {0.default}".format(terule_)
                try:
                    rule_ += " \"{0}\";".format(terule_.filename)
                except (exception.TERuleNoFilename, exception.RuleUseError):
                    # invalid use for type_change/member
                    rule_ += ";"
            else:
                raise RuntimeError("Unhandled TE rule")

            try:
                stmt += "if ({0}) {{\n" \
                        "    {1}\n" \
                        "}}\n".format(terule_.conditional, rule_)
            except exception.RuleNotConditional:
                stmt += "{0}\n".format(rule_)
        stmt += "\n"

        # define roles
        stmt += comment("Define roles identifiers")
        for role_ in cond_sort(self.roles()):
            stmt += "role {0};\n".format(role_)
            # NOTE: the following loop builds statements that are semantically similar to
            # stmt += "{0}\n".format(role_.statement()). It has been splitted in individual
            # statements as checkpolicy's parser has a low YYLMAX limit
            for type_ in role_.types():
                stmt += "role {0} types {1};\n".format(role_, type_)
            stmt += "\n"
        stmt += "\n"

        # define users
        stmt += comment("Define users")
        for user_ in cond_sort(self.users()):
            stmt += "{0}\n".format(user_.statement())
        stmt += "\n"

        # define signature id
        stmt += comment("Define the initial sid contexts")
        for sid_ in cond_sort(self.initialsids()):
            stmt += "{0}\n".format(sid_.statement())
        stmt += "\n"

        # define fs_use contexts
        stmt += comment("Label inodes via fs_use_xxx")
        for fs_use_ in cond_sort(self.fs_uses()):
            stmt += "{0}\n".format(fs_use_.statement())
        stmt += "\n"

        # define genfs contexts
        stmt += comment("Label inodes via genfscon")
        for genfscon_ in cond_sort(self.genfscons()):
            stmt += "{0}\n".format(genfscon_.statement())
        stmt += "\n"

        # define portcon contexts
        stmt += comment("Label ports via portcon")
        for portcon_ in cond_sort(self.portcons()):
            stmt += "{0}\n".format(portcon_.statement())
        stmt += "\n"

        return stmt
