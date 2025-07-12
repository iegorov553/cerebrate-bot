"""
Questions callback handlers.

Handles custom questions management including creation, editing, deletion, and templates.
"""

from telegram import CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.i18n.translator import Translator
from bot.keyboards.keyboard_generators import (
    create_questions_menu,
    create_question_delete_confirm,
    create_question_edit_menu
)
from monitoring import get_logger


logger = get_logger(__name__)


class QuestionsCallbackHandler(BaseCallbackHandler):
    """
    Handles questions-related callback queries.
    
    Responsible for:
    - Questions menu display
    - Question creation, editing, deletion
    - Question templates management
    - Question testing and scheduling
    - Question status toggling (active/inactive)
    """
    
    def can_handle(self, data: str) -> bool:
        """Check if this handler can process the callback data."""
        questions_callbacks = {
            'menu_questions',
            'questions',
            'questions_noop'
        }
        
        return (data in questions_callbacks or 
                data.startswith('questions_'))
    
    async def handle_callback(self, 
                            query: CallbackQuery, 
                            data: str, 
                            translator: Translator, 
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle questions callback queries."""
        
        if data in ["menu_questions", "questions"]:
            await self._handle_questions_menu(query, translator)
            
        elif data == "questions_noop":
            # No-op callback, just answer without action
            pass
            
        elif data.startswith("questions_"):
            await self._handle_questions_action(query, data, translator)
            
        else:
            self.logger.warning("Unhandled questions callback", callback_data=data)
    
    async def _handle_questions_menu(self, 
                                   query: CallbackQuery, 
                                   translator: Translator) -> None:
        """Handle questions menu display."""
        user = query.from_user
        
        try:
            # Initialize question manager
            from bot.questions import QuestionManager
            question_manager = QuestionManager(self.db_client, self.user_cache)
            
            # Get user questions summary
            questions_summary = await question_manager.get_user_questions_summary(user.id)
            
            # Get notifications status from user settings
            from bot.database.user_operations import UserOperations
            user_ops = UserOperations(self.db_client, self.user_cache)
            user_data = await user_ops.get_user_settings(user.id)
            notifications_enabled = user_data.get('enabled', True) if user_data else True
            
            # Create keyboard
            keyboard = create_questions_menu(questions_summary, notifications_enabled, translator)
            
            # Create menu text
            menu_text = f"{translator.translate('questions.title')}\n\n"
            menu_text += translator.translate('questions.description')
            
            await query.edit_message_text(
                menu_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            self.logger.debug("Questions menu displayed", 
                            user_id=user.id,
                            questions_count=len(questions_summary.get('questions', [])))
        
        except Exception as e:
            self.logger.error("Error displaying questions menu", 
                            user_id=user.id, 
                            error=str(e))
            
            # Show error message
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_questions_action(self, 
                                     query: CallbackQuery, 
                                     data: str, 
                                     translator: Translator) -> None:
        """Handle specific questions actions."""
        user = query.from_user
        
        self.logger.debug("Processing questions action", 
                         user_id=user.id, 
                         action=data)
        
        try:
            # Initialize question manager
            from bot.questions import QuestionManager
            question_manager = QuestionManager(self.db_client, self.user_cache)
            
            if data == "questions_create":
                await self._handle_create_question(query, translator)
                
            elif data == "questions_list":
                await self._handle_list_questions(query, question_manager, translator)
                
            elif data == "questions_templates":
                await self._handle_templates_menu(query, translator)
                
            elif data == "questions_back":
                await self._handle_back_to_main(query, translator)
                
            elif data.startswith("questions_edit:"):
                await self._handle_edit_question(query, data, question_manager, translator)
                
            elif data.startswith("questions_delete:"):
                await self._handle_delete_question_confirm(query, data, question_manager, translator)
                
            elif data.startswith("questions_delete_yes:"):
                await self._handle_delete_question_execute(query, data, question_manager, translator)
                
            elif data.startswith("questions_toggle:"):
                await self._handle_toggle_question(query, data, question_manager, translator)
                
            elif data.startswith("questions_test:"):
                await self._handle_test_question(query, data, question_manager, translator)
                
            elif data.startswith("questions_templates_cat:"):
                await self._handle_templates_category(query, data, translator)
                
            elif data.startswith("questions_use_template:"):
                await self._handle_use_template(query, data, question_manager, translator)
                
            elif data.startswith("questions_create_from_template:"):
                await self._handle_create_from_template(query, data, question_manager, translator)
                
            else:
                self.logger.warning("Unknown questions action", 
                                  user_id=user.id, 
                                  action=data)
                # Fallback to questions menu
                await self._handle_questions_menu(query, translator)
        
        except Exception as e:
            self.logger.error("Error in questions action", 
                            user_id=user.id, 
                            action=data,
                            error=str(e))
            
            # Show error and fallback to questions menu
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_create_question(self, 
                                    query: CallbackQuery, 
                                    translator: Translator) -> None:
        """Handle question creation instruction."""
        await query.edit_message_text(
            translator.translate('questions.create_instruction'),
            parse_mode='Markdown'
        )
        
        self.logger.debug("Create question instruction shown", 
                         user_id=query.from_user.id)
    
    async def _handle_list_questions(self, 
                                   query: CallbackQuery, 
                                   question_manager, 
                                   translator: Translator) -> None:
        """Handle questions list display."""
        user = query.from_user
        
        # Get user questions
        questions = await question_manager.question_ops.get_user_questions(user.id)
        
        if not questions:
            # No questions found
            await query.edit_message_text(
                translator.translate('questions.list_empty'),
                parse_mode='Markdown'
            )
            return
        
        # Create questions list text
        list_text = f"{translator.translate('questions.list_title')}\n\n"
        
        for i, question in enumerate(questions[:10], 1):  # Show max 10
            status_emoji = "✅" if question['active'] else "❌"
            question_text = question['question_text'][:50] + "..." if len(question['question_text']) > 50 else question['question_text']
            
            list_text += f"{i}. {status_emoji} {question_text}\n"
            list_text += f"   ⏰ {question['window_start']}-{question['window_end']}, "
            list_text += f"каждые {question['interval_minutes']} мин\n\n"
        
        if len(questions) > 10:
            list_text += f"...и ещё {len(questions) - 10} вопросов"
        
        await query.edit_message_text(
            list_text,
            parse_mode='Markdown'
        )
        
        self.logger.debug("Questions list displayed", 
                         user_id=user.id,
                         questions_count=len(questions))
    
    async def _handle_templates_menu(self, 
                                   query: CallbackQuery, 
                                   translator: Translator) -> None:
        """Handle templates menu display."""
        # This would show template categories
        await query.edit_message_text(
            translator.translate('questions.templates_help'),
            parse_mode='Markdown'
        )
        
        self.logger.debug("Templates menu displayed", 
                         user_id=query.from_user.id)
    
    async def _handle_edit_question(self, 
                                  query: CallbackQuery, 
                                  data: str, 
                                  question_manager, 
                                  translator: Translator) -> None:
        """Handle question editing interface."""
        user = query.from_user
        
        try:
            # Extract question ID
            question_id = int(data.split(":")[1])
            question = await question_manager.question_ops.get_question_by_id(question_id)
            
            if not question:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
                return
            
            # Create edit menu
            keyboard = create_question_edit_menu(question, translator)
            
            # Create edit text
            edit_text = f"{translator.translate('questions.edit_title')}\n\n"
            edit_text += translator.translate('questions.current_text', text=question['question_text']) + "\n"
            edit_text += translator.translate('questions.current_schedule', 
                start=question['window_start'], 
                end=question['window_end'], 
                interval=question['interval_minutes']) + "\n"
            
            status = translator.translate('questions.enable') if question['active'] else translator.translate('questions.disable')
            edit_text += translator.translate('questions.current_status', status=status) + "\n\n"
            edit_text += translator.translate('questions.edit_instructions')
            
            await query.edit_message_text(
                edit_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            self.logger.debug("Question edit interface shown", 
                            user_id=user.id,
                            question_id=question_id)
        
        except (ValueError, IndexError) as e:
            self.logger.error("Invalid question edit callback data", 
                            user_id=user.id, 
                            data=data,
                            error=str(e))
            
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_delete_question_confirm(self, 
                                            query: CallbackQuery, 
                                            data: str, 
                                            question_manager, 
                                            translator: Translator) -> None:
        """Handle question deletion confirmation."""
        user = query.from_user
        
        try:
            # Extract question ID
            question_id = int(data.split(":")[1])
            question = await question_manager.question_ops.get_question_by_id(question_id)
            
            if not question:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
                return
            
            # Create confirmation keyboard
            keyboard = create_question_delete_confirm(question_id, translator)
            
            # Create confirmation text
            confirm_text = f"{translator.translate('questions.delete_confirm')}\n\n"
            confirm_text += f"❓ **{question['question_text']}**\n\n"
            confirm_text += translator.translate('questions.delete_warning')
            
            await query.edit_message_text(
                confirm_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            self.logger.debug("Question delete confirmation shown", 
                            user_id=user.id,
                            question_id=question_id)
        
        except (ValueError, IndexError) as e:
            self.logger.error("Invalid question delete callback data", 
                            user_id=user.id, 
                            data=data,
                            error=str(e))
            
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_delete_question_execute(self, 
                                            query: CallbackQuery, 
                                            data: str, 
                                            question_manager, 
                                            translator: Translator) -> None:
        """Execute question deletion."""
        user = query.from_user
        
        try:
            # Extract question ID
            question_id = int(data.split(":")[1])
            
            # Delete question
            success = await question_manager.question_ops.delete_question(question_id)
            
            if success:
                await query.edit_message_text(
                    translator.translate('questions.delete_success'),
                    parse_mode='Markdown'
                )
                
                self.logger.info("Question deleted", 
                               user_id=user.id,
                               question_id=question_id)
            else:
                await query.edit_message_text(
                    translator.translate('questions.delete_error'),
                    parse_mode='Markdown'
                )
                
                self.logger.error("Failed to delete question", 
                                user_id=user.id,
                                question_id=question_id)
        
        except (ValueError, IndexError) as e:
            self.logger.error("Invalid question delete execute callback data", 
                            user_id=user.id, 
                            data=data,
                            error=str(e))
            
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_toggle_question(self, 
                                    query: CallbackQuery, 
                                    data: str, 
                                    question_manager, 
                                    translator: Translator) -> None:
        """Handle question status toggle (active/inactive)."""
        user = query.from_user
        
        try:
            # Extract question ID
            question_id = int(data.split(":")[1])
            
            # Toggle question status
            success = await question_manager.question_ops.toggle_question_status(question_id)
            
            if success:
                await query.edit_message_text(
                    translator.translate('questions.toggle_success'),
                    parse_mode='Markdown'
                )
                
                self.logger.info("Question status toggled", 
                               user_id=user.id,
                               question_id=question_id)
            else:
                await query.edit_message_text(
                    translator.translate('questions.toggle_error'),
                    parse_mode='Markdown'
                )
                
                self.logger.error("Failed to toggle question status", 
                                user_id=user.id,
                                question_id=question_id)
        
        except (ValueError, IndexError) as e:
            self.logger.error("Invalid question toggle callback data", 
                            user_id=user.id, 
                            data=data,
                            error=str(e))
            
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_test_question(self, 
                                  query: CallbackQuery, 
                                  data: str, 
                                  question_manager, 
                                  translator: Translator) -> None:
        """Handle question testing."""
        user = query.from_user
        
        try:
            # Extract question ID
            question_id = int(data.split(":")[1])
            
            # Send test question
            success = await question_manager.send_test_question(user.id, question_id)
            
            if success:
                await query.edit_message_text(
                    translator.translate('questions.test_sent'),
                    parse_mode='Markdown'
                )
                
                self.logger.info("Test question sent", 
                               user_id=user.id,
                               question_id=question_id)
            else:
                await query.edit_message_text(
                    translator.translate('questions.test_error'),
                    parse_mode='Markdown'
                )
                
                self.logger.error("Failed to send test question", 
                                user_id=user.id,
                                question_id=question_id)
        
        except (ValueError, IndexError) as e:
            self.logger.error("Invalid question test callback data", 
                            user_id=user.id, 
                            data=data,
                            error=str(e))
            
            await query.edit_message_text(
                translator.translate('errors.general'),
                parse_mode='Markdown'
            )
    
    async def _handle_templates_category(self, 
                                       query: CallbackQuery, 
                                       data: str, 
                                       translator: Translator) -> None:
        """Handle template category selection."""
        # This would show templates in specific category
        await query.edit_message_text(
            translator.translate('questions.templates_category_help'),
            parse_mode='Markdown'
        )
        
        self.logger.debug("Template category accessed", 
                         user_id=query.from_user.id,
                         category=data)
    
    async def _handle_use_template(self, 
                                 query: CallbackQuery, 
                                 data: str, 
                                 question_manager, 
                                 translator: Translator) -> None:
        """Handle template usage."""
        # This would show template details and options
        await query.edit_message_text(
            translator.translate('questions.template_use_help'),
            parse_mode='Markdown'
        )
        
        self.logger.debug("Template use interface shown", 
                         user_id=query.from_user.id,
                         template=data)
    
    async def _handle_create_from_template(self, 
                                         query: CallbackQuery, 
                                         data: str, 
                                         question_manager, 
                                         translator: Translator) -> None:
        """Handle question creation from template."""
        # This would create a question from the selected template
        await query.edit_message_text(
            translator.translate('questions.template_create_help'),
            parse_mode='Markdown'
        )
        
        self.logger.debug("Question creation from template initiated", 
                         user_id=query.from_user.id,
                         template=data)
    
    async def _handle_back_to_main(self, 
                                 query: CallbackQuery, 
                                 translator: Translator) -> None:
        """Handle back to main menu."""
        user = query.from_user
        
        # Check if user is admin
        is_admin = (self.config.is_admin_configured() and 
                   user.id == self.config.admin_user_id)
        
        # Generate main menu
        keyboard = KeyboardGenerator.main_menu(is_admin, translator)
        
        # Create welcome message
        welcome_text = f"👋 {translator.translate('welcome.greeting', name=user.first_name)}\n\n"
        welcome_text += translator.translate('welcome.description')
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        self.logger.debug("Returned to main menu from questions", user_id=user.id)